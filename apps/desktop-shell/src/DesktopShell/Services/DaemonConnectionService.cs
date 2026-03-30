using Grpc.Core;
using Grpc.Net.Client;
using Sinapse.Contracts.V1;

namespace DesktopShell.Services;

public sealed class DaemonConnectionService
{
    private readonly string _daemonEndpoint;

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
                ErrorMessage: null);
        }
        catch (RpcException ex)
        {
            return new SendMessageResult(
                IsSuccess: false,
                ConversationId: conversationId,
                UserMessage: null,
                AssistantMessage: null,
                ErrorMessage: $"Daemon error: {ex.Status.Detail}");
        }
        catch (Exception ex)
        {
            return new SendMessageResult(
                IsSuccess: false,
                ConversationId: conversationId,
                UserMessage: null,
                AssistantMessage: null,
                ErrorMessage: ex.Message);
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
            ErrorMessage: $"Could not connect to daemon: {errorDetail}");
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
    string? ErrorMessage);

public sealed record SendMessageResult(
    bool IsSuccess,
    string? ConversationId,
    ChatMessageDto? UserMessage,
    ChatMessageDto? AssistantMessage,
    string? ErrorMessage);
