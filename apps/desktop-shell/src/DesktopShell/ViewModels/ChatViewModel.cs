using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using DesktopShell.Services;
using Sinapse.Contracts.V1;

namespace DesktopShell.ViewModels;

public enum WorkspaceAccessMode
{
    ReadOnly,
    ReadWrite,
}

public sealed class WorkspaceRootViewModel
{
    public required string DisplayName { get; init; }

    public required string RootPath { get; init; }

    public required string AccessModeLabel { get; init; }

    public required string InventorySummary { get; init; }

    public required string SampleFileList { get; init; }
}

public sealed class ChatMessageViewModel
{
    public required string MessageId { get; init; }

    public required string SenderName { get; init; }

    public required string Content { get; init; }

    public required string Timestamp { get; init; }

    public bool IsAssistant { get; init; }

    public bool HasWarnings { get; init; }

    public string WarningBannerText => HasWarnings ? "⚠ Includes warnings" : string.Empty;

    public required string HandlerLabel { get; init; }

    public ObservableCollection<SearchSourceViewModel> Sources { get; init; } = [];

    public bool HasSources => Sources.Count > 0;
}

public sealed class SearchSourceViewModel
{
    public required string Title { get; init; }

    public required string Url { get; init; }
}

public class ChatViewModel : INotifyPropertyChanged
{
    private readonly DaemonConnectionService _daemonConnectionService;
    private readonly PushToTalkRecorderService _pushToTalkRecorderService;
    private readonly SpeechPlaybackService _speechPlaybackService;
    private string? _conversationId;
    private bool _isSending;
    private bool _isPushToTalkListening;
    private bool _isPushToTalkTranscribing;
    private string _pendingMessageText = string.Empty;
    private string _statusText = "Type a message and click Send to test end-to-end chat.";
    private string _workspaceStatusText = "No folders attached yet.";
    private string _pushToTalkStatusText = "Push-to-Talk is ready. Hold the button while speaking.";

    public ChatViewModel(
        DaemonConnectionService daemonConnectionService,
        PushToTalkRecorderService pushToTalkRecorderService,
        SpeechPlaybackService speechPlaybackService)
    {
        _daemonConnectionService = daemonConnectionService;
        _pushToTalkRecorderService = pushToTalkRecorderService;
        _speechPlaybackService = speechPlaybackService;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public event EventHandler<string>? ConversationChanged;

    public string WorkspaceAttachmentTitle { get; } = "Attach folders to this conversation";

    public string WorkspaceAttachmentHelpText { get; } = "Add one or more folders to help the assistant understand your project context. You can start with a single folder and add more later.";

    public ObservableCollection<WorkspaceRootViewModel> AttachedWorkspaceRoots { get; } = [];

    public WorkspaceAccessMode SelectedAccessMode { get; } = WorkspaceAccessMode.ReadOnly;

    public string WorkspaceModeLabel => SelectedAccessMode == WorkspaceAccessMode.ReadOnly
        ? "Read-only workspace"
        : "Read-write workspace";

    public string WorkspaceModeDescription => SelectedAccessMode == WorkspaceAccessMode.ReadOnly
        ? "Recommended for first-time setup. The assistant can inspect files but cannot change them."
        : "Allows file edits after explicit confirmation flow is implemented.";

    public string WorkspaceRootDisplayTitle { get; } = "Visible workspace roots";

    public string WorkspaceRootDisplayDescription { get; } = "Attached folder roots appear here so you can confirm exactly what the assistant can access.";

    public string AddFolderButtonLabel { get; } = "Add folder";

    public string QuickActionExamplesTitle { get; } = "Try these starter actions";

    public string QuickActionExamplesText { get; } =
        "• Analyze these FRD and ZMA files\n" +
        "• Open REW and import these files\n" +
        "• Suggest a crossover region\n" +
        "• Summarize this speaker-design folder";

    public ObservableCollection<ChatMessageViewModel> Messages { get; } = [];

    public bool IsSending
    {
        get => _isSending;
        private set => SetProperty(ref _isSending, value);
    }

    public bool IsPushToTalkListening
    {
        get => _isPushToTalkListening;
        private set
        {
            if (SetProperty(ref _isPushToTalkListening, value))
            {
                OnPropertyChanged(nameof(CanUsePushToTalk));
            }
        }
    }

    public bool IsPushToTalkTranscribing
    {
        get => _isPushToTalkTranscribing;
        private set
        {
            if (SetProperty(ref _isPushToTalkTranscribing, value))
            {
                OnPropertyChanged(nameof(CanUsePushToTalk));
            }
        }
    }

    public string PushToTalkStatusText
    {
        get => _pushToTalkStatusText;
        private set => SetProperty(ref _pushToTalkStatusText, value);
    }

    public string PendingMessageText
    {
        get => _pendingMessageText;
        set
        {
            if (SetProperty(ref _pendingMessageText, value))
            {
                OnPropertyChanged(nameof(CanSendMessage));
            }
        }
    }

    public string StatusText
    {
        get => _statusText;
        private set => SetProperty(ref _statusText, value);
    }

    public string WorkspaceStatusText
    {
        get => _workspaceStatusText;
        private set => SetProperty(ref _workspaceStatusText, value);
    }

    public bool HasAttachedWorkspaceRoots => AttachedWorkspaceRoots.Count > 0;

    public bool CanSendMessage => !IsSending && !string.IsNullOrWhiteSpace(PendingMessageText);

    public bool CanUsePushToTalk => !IsSending && !IsPushToTalkTranscribing;

    public async Task BeginPushToTalkAsync(CancellationToken cancellationToken = default)
    {
        if (!CanUsePushToTalk || IsPushToTalkListening)
        {
            return;
        }

        try
        {
            IsPushToTalkListening = true;
            PushToTalkStatusText = "Listening... release the button when you finish speaking.";
            await _pushToTalkRecorderService.StartRecordingAsync();
        }
        catch (Exception ex)
        {
            IsPushToTalkListening = false;
            PushToTalkStatusText = $"Could not start microphone recording. Please check microphone permissions. ({ex.Message})";
        }
    }

    public async Task EndPushToTalkAsync(CancellationToken cancellationToken = default)
    {
        if (!IsPushToTalkListening)
        {
            return;
        }

        IsPushToTalkListening = false;
        IsPushToTalkTranscribing = true;
        PushToTalkStatusText = "Transcribing your speech...";

        try
        {
            var audioBytes = await _pushToTalkRecorderService.StopRecordingAsync();
            if (audioBytes.Length == 0)
            {
                PushToTalkStatusText = "No speech was captured. Hold Push-to-Talk and speak clearly, then try again.";
                return;
            }

            var result = await _daemonConnectionService.TranscribeAudioAsync(audioBytes, cancellationToken);
            if (!result.IsSuccess)
            {
                PushToTalkStatusText = result.ErrorMessage ?? "Speech transcription is currently unavailable.";
                return;
            }

            PendingMessageText = string.IsNullOrWhiteSpace(PendingMessageText)
                ? result.Transcript
                : $"{PendingMessageText.TrimEnd()} {result.Transcript}";
            PushToTalkStatusText = "Transcription inserted into your message box. Review and press Send when ready.";
        }
        catch (Exception ex)
        {
            PushToTalkStatusText = $"Transcription failed. Please try again. ({ex.Message})";
        }
        finally
        {
            IsPushToTalkTranscribing = false;
        }
    }

    public async Task SendMessageAsync(CancellationToken cancellationToken = default)
    {
        if (!CanSendMessage)
        {
            return;
        }

        var content = PendingMessageText.Trim();
        IsSending = true;
        OnPropertyChanged(nameof(CanSendMessage));
        StatusText = "Sending message to daemon...";

        var result = await _daemonConnectionService.SendUserMessageAsync(_conversationId, content, cancellationToken);

        IsSending = false;
        OnPropertyChanged(nameof(CanSendMessage));

        if (!result.IsSuccess || result.UserMessage is null || result.AssistantMessage is null || result.Conversation is null)
        {
            StatusText = result.ErrorMessage ?? "Failed to send message to daemon.";
            return;
        }

        _conversationId = result.ConversationId;
        PendingMessageText = string.Empty;

        Messages.Add(MapMessage(result.UserMessage));
        Messages.Add(MapMessage(result.AssistantMessage, result.SearchResult?.Sources));

        ConversationChanged?.Invoke(this, result.Conversation.ConversationId);
        await RefreshWorkspaceAsync(cancellationToken);

        var spokenReplyStatus = await MaybeSpeakAssistantReplyAsync(result.AssistantMessage.Content, cancellationToken);
        StatusText = $"Message round-trip completed and persisted. {spokenReplyStatus}".Trim();
    }

    private async Task<string> MaybeSpeakAssistantReplyAsync(string replyText, CancellationToken cancellationToken)
    {
        var settings = await _daemonConnectionService.GetAppSettingsAsync(cancellationToken);
        if (!settings.IsSuccess || settings.Settings is null || !(settings.Settings.SpeechSettings?.SpokenRepliesEnabled ?? false))
        {
            return "";
        }

        var ttsResult = await _daemonConnectionService.SynthesizeSpeechAsync(replyText, cancellationToken);
        if (!ttsResult.IsSuccess)
        {
            return ttsResult.ErrorMessage ?? "Spoken reply failed.";
        }

        var played = await _speechPlaybackService.PlayWavAsync(ttsResult.AudioBytes);
        return played ? "Assistant reply was spoken aloud." : _speechPlaybackService.LastStatus;
    }

    public async Task LoadConversationAsync(string conversationId, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(conversationId))
        {
            return;
        }

        StatusText = "Loading conversation history...";
        var result = await _daemonConnectionService.GetConversationAsync(conversationId, cancellationToken);
        if (!result.IsSuccess || result.Conversation is null)
        {
            StatusText = result.ErrorMessage ?? "Failed to load conversation.";
            return;
        }

        _conversationId = result.Conversation.ConversationId;
        Messages.Clear();
        foreach (var message in result.Messages)
        {
            Messages.Add(MapMessage(message));
        }

        StatusText = $"Loaded conversation '{result.Conversation.Title}' from SQLite.";
        await RefreshWorkspaceAsync(cancellationToken);
        ConversationChanged?.Invoke(this, _conversationId);
    }

    public async Task AttachFolderAsync(
        string rootPath,
        WorkspaceAccessMode selectedMode,
        CancellationToken cancellationToken = default)
    {
        WorkspaceStatusText = "Attaching folder and scanning files...";
        var requestMode = selectedMode == WorkspaceAccessMode.ReadWrite
            ? Sinapse.Contracts.V1.WorkspaceAccessMode.ReadWrite
            : Sinapse.Contracts.V1.WorkspaceAccessMode.ReadOnly;

        var result = await _daemonConnectionService.AttachWorkspaceRootAsync(
            _conversationId,
            rootPath,
            requestMode,
            cancellationToken);

        if (!result.IsSuccess || string.IsNullOrWhiteSpace(result.ConversationId))
        {
            WorkspaceStatusText = result.ErrorMessage ?? "Failed to attach workspace root.";
            return;
        }

        _conversationId = result.ConversationId;
        ConversationChanged?.Invoke(this, result.ConversationId);

        await RefreshWorkspaceAsync(cancellationToken);
        WorkspaceStatusText = "Workspace root attached and inventory refreshed.";
    }

    private async Task RefreshWorkspaceAsync(CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(_conversationId))
        {
            AttachedWorkspaceRoots.Clear();
            WorkspaceStatusText = "No conversation selected. Attach a folder to start workspace context.";
            OnPropertyChanged(nameof(HasAttachedWorkspaceRoots));
            return;
        }

        var workspace = await _daemonConnectionService.GetConversationWorkspaceAsync(_conversationId, cancellationToken);
        if (!workspace.IsSuccess)
        {
            WorkspaceStatusText = workspace.ErrorMessage ?? "Failed to load workspace roots.";
            return;
        }

        AttachedWorkspaceRoots.Clear();
        foreach (var root in workspace.Roots)
        {
            AttachedWorkspaceRoots.Add(MapWorkspaceRoot(root));
        }

        WorkspaceStatusText = AttachedWorkspaceRoots.Count == 0
            ? "No folders attached yet."
            : $"Showing {AttachedWorkspaceRoots.Count} attached workspace root(s).";
        OnPropertyChanged(nameof(HasAttachedWorkspaceRoots));
    }

    private static WorkspaceRootViewModel MapWorkspaceRoot(WorkspaceRootDto root)
    {
        var modeLabel = root.AccessMode == Sinapse.Contracts.V1.WorkspaceAccessMode.ReadWrite
            ? "Read-write"
            : "Read-only";
        var fileCount = (int)root.FileCount;
        var inventorySummary = fileCount == 0
            ? "No files discovered yet."
            : $"{fileCount} file(s) discovered";

        var sampleFileList = root.SampleFiles.Count == 0
            ? "No sample files available."
            : string.Join(Environment.NewLine, root.SampleFiles.Take(10).Select(item => $"• {item}"));

        return new WorkspaceRootViewModel
        {
            DisplayName = root.DisplayName,
            RootPath = root.RootPath,
            AccessModeLabel = modeLabel,
            InventorySummary = inventorySummary,
            SampleFileList = sampleFileList,
        };
    }

    private static ChatMessageViewModel MapMessage(
        ChatMessageDto message,
        IReadOnlyList<SearchSourceDto>? sources = null)
    {
        var sourceViewModels = sources is null
            ? []
            : [.. sources
                .Where(source => !string.IsNullOrWhiteSpace(source.Url))
                .Select(source => new SearchSourceViewModel
                {
                    Title = string.IsNullOrWhiteSpace(source.Title) ? "Source" : source.Title,
                    Url = source.Url,
                })];

        return new ChatMessageViewModel
        {
            MessageId = message.MessageId,
            SenderName = message.Role == MessageRole.Assistant ? "Assistant" : "You",
            Content = message.Content,
            Timestamp = message.CreatedAt,
            IsAssistant = message.Role == MessageRole.Assistant,
            HasWarnings = message.Role == MessageRole.Assistant && ContainsWarning(message.Content),
            HandlerLabel = BuildHandlerLabel(message),
            Sources = sourceViewModels,
        };
    }

    private static bool ContainsWarning(string content)
    {
        if (string.IsNullOrWhiteSpace(content))
        {
            return false;
        }

        var normalized = content.ToLowerInvariant();
        return normalized.Contains("⚠") || normalized.Contains("warning");
    }

    private static string BuildHandlerLabel(ChatMessageDto message)
    {
        if (message.Role != MessageRole.Assistant)
        {
            return string.Empty;
        }

        var provider = string.IsNullOrWhiteSpace(message.ProviderId) ? "unknown-provider" : message.ProviderId;
        var model = string.IsNullOrWhiteSpace(message.ModelId) ? "unknown-model" : message.ModelId;
        return $"Handled by {provider} · {model}";
    }

    private bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return false;
        }

        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }

    private void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
