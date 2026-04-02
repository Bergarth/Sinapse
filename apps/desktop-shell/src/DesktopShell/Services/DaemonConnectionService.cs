using Google.Protobuf;
using Grpc.Core;
using Grpc.Net.Client;
using Sinapse.Contracts.V1;
using System.IO;

namespace DesktopShell.Services;

public sealed class DaemonConnectionService
{
    private readonly string _daemonEndpoint;
    private CancellationTokenSource? _observationCts;

    public DaemonConnectionService(string? daemonEndpoint = null)
    {
        _daemonEndpoint = daemonEndpoint
            ?? Environment.GetEnvironmentVariable("AGENT_DAEMON_ENDPOINT")
            ?? "http://127.0.0.1:50051";
    }

    public async Task<DaemonConnectionResult> GetStartupStatusAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.HealthCheckAsync(
                new HealthCheckRequest { Requester = "desktop-shell" },
                cancellationToken: cancellationToken);

            var isConnected = response.Daemon.Status == HealthStatus.Healthy;
            var lastSuccessfulConnectionUtc = isConnected ? DateTimeOffset.UtcNow : null;

            return new DaemonConnectionResult(
                IsConnected: isConnected,
                Endpoint: _daemonEndpoint,
                DaemonStatus: response.Daemon.Detail,
                DaemonVersion: response.DaemonVersion,
                EnvironmentStatus: response.System.Detail,
                EnvironmentName: response.System.Environment,
                LastSuccessfulConnectionUtc: lastSuccessfulConnectionUtc,
                Capabilities: response.Capabilities,
                ErrorMessage: null);
        }
        catch (RpcException ex)
        {
            return DisconnectedResult(_daemonEndpoint, ex.Status.Detail);
        }
        catch (Exception ex)
        {
            return DisconnectedResult(_daemonEndpoint, ex.Message);
        }
    }


    public async Task<GetAppSettingsResult> GetAppSettingsAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.GetAppSettingsAsync(
                new GetAppSettingsRequest { Requester = "desktop-shell" },
                cancellationToken: cancellationToken);

            return new GetAppSettingsResult(true, response.Settings, null);
        }
        catch (RpcException ex)
        {
            return new GetAppSettingsResult(false, null, $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new GetAppSettingsResult(false, null, ex.Message);
        }
    }

    public async Task<UpdateAppSettingsResult> UpdateAppSettingsAsync(
        AppSettingsDto settings,
        CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.UpdateAppSettingsAsync(
                new UpdateAppSettingsRequest
                {
                    Settings = settings,
                    UpdatedBy = "desktop-shell",
                },
                cancellationToken: cancellationToken);

            return new UpdateAppSettingsResult(true, response.Settings, null);
        }
        catch (RpcException ex)
        {
            return new UpdateAppSettingsResult(false, null, $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new UpdateAppSettingsResult(false, null, ex.Message);
        }
    }

    public async Task<SendMessageResult> SendUserMessageAsync(
        string? conversationId,
        string userContent,
        CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);

            var resolvedConversationId = conversationId;
            if (string.IsNullOrWhiteSpace(resolvedConversationId))
            {
                var startResponse = await client.StartConversationAsync(
                    new StartConversationRequest
                    {
                        WorkspaceId = "desktop-shell-workspace",
                        Title = "Desktop Shell Chat",
                        InitiatedBy = "desktop-shell",
                    },
                    cancellationToken: cancellationToken);
                resolvedConversationId = startResponse.Conversation.ConversationId;
            }

            var now = DateTimeOffset.UtcNow.ToString("O");
            var sendResponse = await client.SendUserMessageAsync(
                new SendUserMessageRequest
                {
                    ConversationId = resolvedConversationId,
                    UserMessageId = $"user-{Guid.NewGuid():N}",
                    Content = userContent,
                    SentAt = now,
                },
                cancellationToken: cancellationToken);

            return new SendMessageResult(
                IsSuccess: true,
                ConversationId: sendResponse.Conversation.ConversationId,
                UserMessage: sendResponse.UserMessage,
                AssistantMessage: sendResponse.AssistantMessage,
                SearchResult: sendResponse.SearchResult,
                Conversation: sendResponse.Conversation,
                ErrorMessage: null);
        }
        catch (RpcException ex)
        {
            return new SendMessageResult(
                IsSuccess: false,
                ConversationId: conversationId,
                UserMessage: null,
                AssistantMessage: null,
                SearchResult: null,
                Conversation: null,
                ErrorMessage: $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new SendMessageResult(
                IsSuccess: false,
                ConversationId: conversationId,
                UserMessage: null,
                AssistantMessage: null,
                SearchResult: null,
                Conversation: null,
                ErrorMessage: ex.Message);
        }
    }

    public async Task<AttachWorkspaceRootResult> AttachWorkspaceRootAsync(
        string? conversationId,
        string rootPath,
        WorkspaceAccessMode accessMode,
        CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.AttachWorkspaceRootAsync(
                new AttachWorkspaceRootRequest
                {
                    ConversationId = conversationId ?? string.Empty,
                    RootPath = rootPath,
                    DisplayName = Path.GetFileName(rootPath),
                    AccessMode = accessMode,
                    RequestedBy = "desktop-shell",
                },
                cancellationToken: cancellationToken);

            return new AttachWorkspaceRootResult(
                IsSuccess: true,
                ConversationId: response.Conversation.ConversationId,
                Root: response.Root,
                ErrorMessage: null);
        }
        catch (RpcException ex)
        {
            return new AttachWorkspaceRootResult(
                IsSuccess: false,
                ConversationId: conversationId,
                Root: null,
                ErrorMessage: $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new AttachWorkspaceRootResult(
                IsSuccess: false,
                ConversationId: conversationId,
                Root: null,
                ErrorMessage: ex.Message);
        }
    }

    public async Task<GetConversationWorkspaceResult> GetConversationWorkspaceAsync(
        string conversationId,
        CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.GetConversationWorkspaceAsync(
                new GetConversationWorkspaceRequest { ConversationId = conversationId },
                cancellationToken: cancellationToken);

            return new GetConversationWorkspaceResult(
                IsSuccess: true,
                ConversationId: response.ConversationId,
                Roots: response.Roots,
                ErrorMessage: null);
        }
        catch (RpcException ex)
        {
            return new GetConversationWorkspaceResult(false, conversationId, [], $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new GetConversationWorkspaceResult(false, conversationId, [], ex.Message);
        }
    }

    public async Task<IReadOnlyList<ConversationDto>> ListConversationsAsync(CancellationToken cancellationToken = default)
    {
        using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
        var client = new DaemonContract.DaemonContractClient(channel);
        var response = await client.ListConversationsAsync(new ListConversationsRequest(), cancellationToken: cancellationToken);
        return response.Conversations;
    }

    public async Task<GetConversationResult> GetConversationAsync(string conversationId, CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);

            var response = await client.GetConversationAsync(
                new GetConversationRequest { ConversationId = conversationId },
                cancellationToken: cancellationToken);

            return new GetConversationResult(
                IsSuccess: true,
                Conversation: response.Conversation,
                Messages: response.Messages,
                ErrorMessage: null);
        }
        catch (RpcException ex)
        {
            return new GetConversationResult(false, null, [], $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new GetConversationResult(false, null, [], ex.Message);
        }
    }

    public async Task<StartTaskResult> StartTaskAsync(
        string? conversationId,
        string title,
        CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.StartTaskAsync(
                new StartTaskRequest
                {
                    ConversationId = conversationId ?? string.Empty,
                    Title = title,
                    RequestedBy = "desktop-shell",
                },
                cancellationToken: cancellationToken);

            return new StartTaskResult(true, response.Task, null);
        }
        catch (RpcException ex)
        {
            return new StartTaskResult(false, null, $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new StartTaskResult(false, null, ex.Message);
        }
    }

    public async Task<ApproveStepResult> ApproveStepAsync(
        string taskId,
        string stepId,
        bool approve,
        string note,
        CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.ApproveStepAsync(
                new ApproveStepRequest
                {
                    TaskId = taskId,
                    StepId = stepId,
                    ApprovedBy = "desktop-shell",
                    Note = approve ? note : $"deny: {note}",
                    ApprovedAt = DateTimeOffset.UtcNow.ToString("O"),
                },
                cancellationToken: cancellationToken);

            return new ApproveStepResult(true, response.TaskId, response.StepId, response.ApprovalStatus, null);
        }
        catch (RpcException ex)
        {
            return new ApproveStepResult(false, taskId, stepId, ApprovalStatus.Unspecified, $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new ApproveStepResult(false, taskId, stepId, ApprovalStatus.Unspecified, ex.Message);
        }
    }

    public async Task<CancelTaskResult> CancelTaskAsync(
        string taskId,
        string reason,
        CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.CancelTaskAsync(
                new CancelTaskRequest
                {
                    TaskId = taskId,
                    Reason = reason,
                    CanceledBy = "desktop-shell",
                    CanceledAt = DateTimeOffset.UtcNow.ToString("O"),
                },
                cancellationToken: cancellationToken);

            return new CancelTaskResult(true, response.Task, null);
        }
        catch (RpcException ex)
        {
            return new CancelTaskResult(false, null, $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new CancelTaskResult(false, null, ex.Message);
        }
    }


    public async Task<TranscribeAudioResult> TranscribeAudioAsync(byte[] audioWav, CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.TranscribeAudioAsync(
                new TranscribeAudioRequest
                {
                    AudioWav = ByteString.CopyFrom(audioWav),
                    AudioMimeType = "audio/wav",
                    RequestedBy = "desktop-shell",
                },
                cancellationToken: cancellationToken);

            return new TranscribeAudioResult(true, response.Transcript, response.Detail, null);
        }
        catch (RpcException ex)
        {
            return new TranscribeAudioResult(false, string.Empty, string.Empty, $"Speech transcription error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new TranscribeAudioResult(false, string.Empty, string.Empty, ex.Message);
        }
    }

    public async Task<SynthesizeSpeechResult> SynthesizeSpeechAsync(string text, CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.SynthesizeSpeechAsync(
                new SynthesizeSpeechRequest
                {
                    Text = text,
                    RequestedBy = "desktop-shell",
                },
                cancellationToken: cancellationToken);

            return new SynthesizeSpeechResult(
                true,
                response.AudioWav.ToByteArray(),
                string.IsNullOrWhiteSpace(response.AudioMimeType) ? "audio/wav" : response.AudioMimeType,
                response.Detail,
                null);
        }
        catch (RpcException ex)
        {
            return new SynthesizeSpeechResult(false, [], "audio/wav", string.Empty, $"Speech playback unavailable: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new SynthesizeSpeechResult(false, [], "audio/wav", string.Empty, ex.Message);
        }
    }

    public Task BeginSystemStateObservationAsync(
        Action<SystemStateEvent> onEvent,
        CancellationToken cancellationToken = default)
    {
        _observationCts?.Cancel();
        _observationCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        return Task.Run(() => ObserveSystemStateLoopAsync(onEvent, _observationCts.Token), _observationCts.Token);
    }

    public void StopSystemStateObservation()
    {
        _observationCts?.Cancel();
    }

    private async Task ObserveSystemStateLoopAsync(Action<SystemStateEvent> onEvent, CancellationToken cancellationToken)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            using var stream = client.ObserveSystemState(
                new ObserveSystemStateRequest { WorkspaceId = "desktop-shell-workspace" },
                cancellationToken: cancellationToken);

            while (await stream.ResponseStream.MoveNext(cancellationToken))
            {
                onEvent(stream.ResponseStream.Current);
            }
        }
        catch (OperationCanceledException)
        {
            // no-op; expected during app shutdown or restart.
        }
        catch
        {
            // Keep this first implementation lightweight; timeline displays only received events.
        }
    }

    private static DaemonConnectionResult DisconnectedResult(string endpoint, string errorDetail)
    {
        return new DaemonConnectionResult(
            IsConnected: false,
            Endpoint: endpoint,
            DaemonStatus: "Unavailable",
            DaemonVersion: "unknown",
            EnvironmentStatus: "Unavailable",
            EnvironmentName: "unknown",
            LastSuccessfulConnectionUtc: null,
            Capabilities: [],
            ErrorMessage: $"Could not connect to daemon at {endpoint}. Start agent-daemon first, then retry. Details: {errorDetail}");
    }
}

public sealed record DaemonConnectionResult(
    bool IsConnected,
    string Endpoint,
    string DaemonStatus,
    string DaemonVersion,
    string EnvironmentStatus,
    string EnvironmentName,
    DateTimeOffset? LastSuccessfulConnectionUtc,
    IReadOnlyList<CapabilityStatusDto> Capabilities,
    string? ErrorMessage);

public sealed record SendMessageResult(
    bool IsSuccess,
    string? ConversationId,
    ChatMessageDto? UserMessage,
    ChatMessageDto? AssistantMessage,
    SearchResultDto? SearchResult,
    ConversationDto? Conversation,
    string? ErrorMessage);

public sealed record GetConversationResult(
    bool IsSuccess,
    ConversationDto? Conversation,
    IReadOnlyList<ChatMessageDto> Messages,
    string? ErrorMessage);

public sealed record StartTaskResult(
    bool IsSuccess,
    TaskSummaryDto? Task,
    string? ErrorMessage);

public sealed record ApproveStepResult(
    bool IsSuccess,
    string TaskId,
    string StepId,
    ApprovalStatus ApprovalStatus,
    string? ErrorMessage);

public sealed record CancelTaskResult(
    bool IsSuccess,
    TaskSummaryDto? Task,
    string? ErrorMessage);

public sealed record AttachWorkspaceRootResult(
    bool IsSuccess,
    string? ConversationId,
    WorkspaceRootDto? Root,
    string? ErrorMessage);

public sealed record GetConversationWorkspaceResult(
    bool IsSuccess,
    string ConversationId,
    IReadOnlyList<WorkspaceRootDto> Roots,
    string? ErrorMessage);

public sealed record GetAppSettingsResult(
    bool IsSuccess,
    AppSettingsDto? Settings,
    string? ErrorMessage);

public sealed record UpdateAppSettingsResult(
    bool IsSuccess,
    AppSettingsDto? Settings,
    string? ErrorMessage);


public sealed record TranscribeAudioResult(
    bool IsSuccess,
    string Transcript,
    string Detail,
    string? ErrorMessage);

public sealed record SynthesizeSpeechResult(
    bool IsSuccess,
    byte[] AudioBytes,
    string AudioMimeType,
    string Detail,
    string? ErrorMessage);
