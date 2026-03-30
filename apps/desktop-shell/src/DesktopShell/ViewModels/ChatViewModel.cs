using System.Collections.ObjectModel;
using System.ComponentModel;
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
}

public sealed class ChatMessageViewModel
{
    public required string MessageId { get; init; }

    public required string SenderName { get; init; }

    public required string Content { get; init; }

    public required string Timestamp { get; init; }

    public bool IsAssistant { get; init; }
}

public class ChatViewModel : INotifyPropertyChanged
{
    private readonly DaemonConnectionService _daemonConnectionService;
    private string? _conversationId;
    private bool _isSending;
    private string _pendingMessageText = string.Empty;
    private string _statusText = "Type a message and click Send to test end-to-end chat.";

    public ChatViewModel(DaemonConnectionService daemonConnectionService)
    {
        _daemonConnectionService = daemonConnectionService;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public string WorkspaceAttachmentTitle { get; } = "Attach folders to this conversation";

    public string WorkspaceAttachmentHelpText { get; } = "Add one or more folders to help the assistant understand your project context. You can start with a single folder and add more later.";

    public IReadOnlyList<WorkspaceRootViewModel> AttachedWorkspaceRoots { get; } =
    [
        new WorkspaceRootViewModel
        {
            DisplayName = "No folders attached yet",
            RootPath = "Choose a folder to display its root path here.",
        },
    ];

    public WorkspaceAccessMode SelectedAccessMode { get; } = WorkspaceAccessMode.ReadOnly;

    public string WorkspaceModeLabel => SelectedAccessMode == WorkspaceAccessMode.ReadOnly
        ? "Read-only workspace"
        : "Read-write workspace";

    public string WorkspaceModeDescription => SelectedAccessMode == WorkspaceAccessMode.ReadOnly
        ? "Recommended for first-time setup. The assistant can inspect files but cannot change them."
        : "Allows file edits after explicit confirmation flow is implemented.";

    public string WorkspaceRootDisplayTitle { get; } = "Visible workspace roots";

    public string WorkspaceRootDisplayDescription { get; } = "Attached folder roots appear here so you can confirm exactly what the assistant can access.";

    public string AddFolderButtonLabel { get; } = "Add folder (coming soon)";

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

        if (!result.IsSuccess || result.UserMessage is null || result.AssistantMessage is null)
        {
            StatusText = result.ErrorMessage ?? "Failed to send message to daemon.";
            return;
        }

        _conversationId = result.ConversationId;
        PendingMessageText = string.Empty;

        Messages.Add(MapMessage(result.UserMessage));
        Messages.Add(MapMessage(result.AssistantMessage));

        StatusText = "Message round-trip completed.";
    }

    private static ChatMessageViewModel MapMessage(ChatMessageDto message)
    {
        return new ChatMessageViewModel
        {
            MessageId = message.MessageId,
            SenderName = message.Role == MessageRole.Assistant ? "Assistant" : "You",
            Content = message.Content,
            Timestamp = message.CreatedAt,
            IsAssistant = message.Role == MessageRole.Assistant,
        };
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
