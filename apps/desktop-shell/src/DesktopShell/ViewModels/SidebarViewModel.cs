using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using DesktopShell.Services;
using Sinapse.Contracts.V1;

namespace DesktopShell.ViewModels;

public sealed class ConversationSummaryViewModel
{
    public required string ConversationId { get; init; }

    public required string Title { get; init; }

    public required string UpdatedAt { get; init; }
}

public class SidebarViewModel : INotifyPropertyChanged
{
    private readonly DaemonConnectionService _daemonConnectionService;
    private string? _selectedConversationId;
    private string _statusText = "Loading conversations...";

    public SidebarViewModel(DaemonConnectionService daemonConnectionService)
    {
        _daemonConnectionService = daemonConnectionService;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public event EventHandler<string>? ConversationSelected;

    public ObservableCollection<ConversationSummaryViewModel> Conversations { get; } = [];

    public string StatusText
    {
        get => _statusText;
        private set => SetProperty(ref _statusText, value);
    }

    public string? SelectedConversationId
    {
        get => _selectedConversationId;
        private set => SetProperty(ref _selectedConversationId, value);
    }

    public async Task RefreshConversationsAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            var conversations = await _daemonConnectionService.ListConversationsAsync(cancellationToken);

            Conversations.Clear();
            foreach (var conversation in conversations)
            {
                Conversations.Add(MapConversation(conversation));
            }

            StatusText = Conversations.Count == 0
                ? "No conversations yet. Send your first message to create one."
                : $"{Conversations.Count} conversation(s) loaded from SQLite.";
        }
        catch (Exception ex)
        {
            StatusText = $"Failed to load conversations: {ex.Message}";
        }
    }

    public void SelectConversation(string conversationId)
    {
        if (string.IsNullOrWhiteSpace(conversationId))
        {
            return;
        }

        SelectedConversationId = conversationId;
        ConversationSelected?.Invoke(this, conversationId);
    }

    public void MarkSelectedConversation(string conversationId)
    {
        SelectedConversationId = conversationId;
    }

    private static ConversationSummaryViewModel MapConversation(ConversationDto conversation)
    {
        return new ConversationSummaryViewModel
        {
            ConversationId = conversation.ConversationId,
            Title = string.IsNullOrWhiteSpace(conversation.Title) ? "Untitled conversation" : conversation.Title,
            UpdatedAt = conversation.UpdatedAt,
        };
    }

    private bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return false;
        }

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }
}
