using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using DesktopShell.Services;
using Microsoft.UI.Dispatching;
using Sinapse.Contracts.V1;

namespace DesktopShell.ViewModels;

public sealed class TimelineEntryViewModel
{
    public required string Timestamp { get; init; }

    public required string Title { get; init; }

    public required string Detail { get; init; }

    public required string Emoji { get; init; }
}

public class TaskTimelineViewModel : INotifyPropertyChanged
{
    private readonly DaemonConnectionService _daemonConnectionService;
    private readonly DispatcherQueue _dispatcherQueue;
    private string? _conversationId;
    private bool _isStartingTask;
    private string _statusText = "Run a read-only desktop task to list your open windows.";

    public TaskTimelineViewModel(DaemonConnectionService daemonConnectionService, DispatcherQueue dispatcherQueue)
    {
        _daemonConnectionService = daemonConnectionService;
        _dispatcherQueue = dispatcherQueue;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public ObservableCollection<TimelineEntryViewModel> TimelineEntries { get; } = [];

    public bool IsStartingTask
    {
        get => _isStartingTask;
        private set
        {
            if (SetProperty(ref _isStartingTask, value))
            {
                OnPropertyChanged(nameof(CanStartTask));
            }
        }
    }

    public bool CanStartTask => !IsStartingTask && !string.IsNullOrWhiteSpace(_conversationId);

    public string StatusText
    {
        get => _statusText;
        private set => SetProperty(ref _statusText, value);
    }

    public void SetConversationId(string? conversationId)
    {
        _conversationId = conversationId;
        OnPropertyChanged(nameof(CanStartTask));
    }

    public Task BeginObservingAsync(CancellationToken cancellationToken = default)
    {
        return _daemonConnectionService.BeginSystemStateObservationAsync(OnSystemStateEvent, cancellationToken);
    }

    public async Task StartTaskAsync(CancellationToken cancellationToken = default)
    {
        if (!CanStartTask)
        {
            StatusText = "Send a message first so a conversation exists for this task.";
            return;
        }

        IsStartingTask = true;
        StatusText = "Starting task...";
        var taskTitle = $"List open windows (read-only) {DateTimeOffset.Now:HH:mm:ss}";
        var result = await _daemonConnectionService.StartTaskAsync(_conversationId, taskTitle, cancellationToken);
        IsStartingTask = false;

        StatusText = result.IsSuccess
            ? "Task started. Timeline updates will appear below."
            : (result.ErrorMessage ?? "Failed to start task.");
    }

    private void OnSystemStateEvent(SystemStateEvent stateEvent)
    {
        if (stateEvent.TaskTimelineEvents.Count == 0)
        {
            return;
        }

        _dispatcherQueue.TryEnqueue(() =>
        {
            foreach (var timelineEvent in stateEvent.TaskTimelineEvents)
            {
                TimelineEntries.Insert(0, new TimelineEntryViewModel
                {
                    Timestamp = timelineEvent.ObservedAt,
                    Title = timelineEvent.Title,
                    Detail = timelineEvent.Detail,
                    Emoji = ToEmoji(timelineEvent.EventType),
                });
            }

            if (TimelineEntries.Count > 40)
            {
                while (TimelineEntries.Count > 40)
                {
                    TimelineEntries.RemoveAt(TimelineEntries.Count - 1);
                }
            }

            StatusText = "Timeline updated from daemon stream.";
        });
    }

    private static string ToEmoji(TaskEventType eventType)
    {
        return eventType switch
        {
            TaskEventType.TaskStarted => "🚀",
            TaskEventType.StepStarted => "▶️",
            TaskEventType.StepFinished => "✅",
            TaskEventType.TaskFinished => "🎉",
            TaskEventType.TaskFailed => "❌",
            _ => "•",
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
