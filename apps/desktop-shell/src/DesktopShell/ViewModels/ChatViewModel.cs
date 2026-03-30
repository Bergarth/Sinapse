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
    private string? _conversationId;
    private bool _isSending;
    private string _pendingMessageText = string.Empty;
    private string _statusText = "Type a message and click Send to test end-to-end chat.";
    private string _workspaceStatusText = "No folders attached yet.";

    public ChatViewModel(DaemonConnectionService daemonConnectionService)
    {
        _daemonConnectionService = daemonConnectionService;
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

    public ObservableCollection<ChatMessageViewModel> Messages { get; } = [];

    public bool IsSending
    {
        get => _isSending;
        private set => SetProperty(ref _isSending, value);
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
        StatusText = "Message round-trip completed and persisted.";
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
            HandlerLabel = BuildHandlerLabel(message),
            Sources = sourceViewModels,
        };
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
