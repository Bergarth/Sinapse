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

public sealed class ApprovalPromptViewModel
{
    public required string TaskId { get; init; }
    public required string StepId { get; init; }
    public required string ActionSummary { get; init; }
    public required string Reason { get; init; }
    public required string Target { get; init; }
    public required string RiskClass { get; init; }
}

public class TaskTimelineViewModel : INotifyPropertyChanged
{
    private readonly DaemonConnectionService _daemonConnectionService;
    private readonly DispatcherQueue _dispatcherQueue;
    private string? _conversationId;
    private ApprovalPromptViewModel? _pendingApproval;
    private bool _isStartingTask;
    private bool _isSubmittingApproval;
    private string _statusText = "Run a read-only browser task to open a URL and summarize the page.";

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
    public bool HasPendingApproval => PendingApproval is not null;
    public bool CanRespondToApproval => PendingApproval is not null && !IsSubmittingApproval;

    public ApprovalPromptViewModel? PendingApproval
    {
        get => _pendingApproval;
        private set
        {
            if (SetProperty(ref _pendingApproval, value))
            {
                OnPropertyChanged(nameof(HasPendingApproval));
                OnPropertyChanged(nameof(CanRespondToApproval));
                OnPropertyChanged(nameof(PendingApprovalActionSummary));
                OnPropertyChanged(nameof(PendingApprovalReason));
                OnPropertyChanged(nameof(PendingApprovalTarget));
                OnPropertyChanged(nameof(PendingApprovalRiskClass));
            }
        }
    }

    public bool IsSubmittingApproval
    {
        get => _isSubmittingApproval;
        private set
        {
            if (SetProperty(ref _isSubmittingApproval, value))
            {
                OnPropertyChanged(nameof(CanRespondToApproval));
            }
        }
    }

    public string PendingApprovalActionSummary => PendingApproval?.ActionSummary ?? "(waiting for approval details)";
    public string PendingApprovalReason => PendingApproval?.Reason ?? string.Empty;
    public string PendingApprovalTarget => PendingApproval?.Target ?? "unknown target";
    public string PendingApprovalRiskClass => PendingApproval?.RiskClass ?? "write";

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
        var taskTitle = $"Open https://example.com and summarize it (read-only) {DateTimeOffset.Now:HH:mm:ss}";
        var result = await _daemonConnectionService.StartTaskAsync(_conversationId, taskTitle, cancellationToken);
        IsStartingTask = false;

        StatusText = result.IsSuccess
            ? "Task started. Timeline updates will appear below."
            : (result.ErrorMessage ?? "Failed to start task.");
    }

    public async Task StartRiskyDemoTaskAsync(CancellationToken cancellationToken = default)
    {
        if (!CanStartTask)
        {
            StatusText = "Send a message first so a conversation exists for this task.";
            return;
        }

        IsStartingTask = true;
        StatusText = "Starting risky placeholder task...";
        var taskTitle = $"Write a summary to report.txt and send it to review@example.com {DateTimeOffset.Now:HH:mm:ss}";
        var result = await _daemonConnectionService.StartTaskAsync(_conversationId, taskTitle, cancellationToken);
        IsStartingTask = false;
        StatusText = result.IsSuccess
            ? "Risky demo task started. It should pause for approval."
            : (result.ErrorMessage ?? "Failed to start risky task.");
    }

    public async Task ApprovePendingStepAsync(CancellationToken cancellationToken = default)
    {
        if (!CanRespondToApproval || PendingApproval is null)
        {
            return;
        }

        IsSubmittingApproval = true;
        StatusText = "Sending approval to daemon...";
        var prompt = PendingApproval;
        var result = await _daemonConnectionService.ApproveStepAsync(
            prompt.TaskId,
            prompt.StepId,
            approve: true,
            note: "Approved from shell approval card.",
            cancellationToken);
        IsSubmittingApproval = false;

        if (!result.IsSuccess)
        {
            StatusText = result.ErrorMessage ?? "Failed to submit approval.";
            return;
        }

        PendingApproval = null;
        StatusText = "Approval submitted. Task can continue.";
    }

    public async Task DenyPendingStepAsync(CancellationToken cancellationToken = default)
    {
        if (!CanRespondToApproval || PendingApproval is null)
        {
            return;
        }

        IsSubmittingApproval = true;
        StatusText = "Sending deny decision to daemon...";
        var prompt = PendingApproval;
        var result = await _daemonConnectionService.ApproveStepAsync(
            prompt.TaskId,
            prompt.StepId,
            approve: false,
            note: "Denied from shell approval card.",
            cancellationToken);
        IsSubmittingApproval = false;

        if (!result.IsSuccess)
        {
            StatusText = result.ErrorMessage ?? "Failed to submit deny decision.";
            return;
        }

        PendingApproval = null;
        StatusText = "Denied. Task execution was stopped.";
    }

    public async Task CancelPendingTaskAsync(CancellationToken cancellationToken = default)
    {
        if (!CanRespondToApproval || PendingApproval is null)
        {
            return;
        }

        IsSubmittingApproval = true;
        StatusText = "Canceling task...";
        var prompt = PendingApproval;
        var result = await _daemonConnectionService.CancelTaskAsync(
            prompt.TaskId,
            reason: "Canceled from shell approval card.",
            cancellationToken);
        IsSubmittingApproval = false;

        if (!result.IsSuccess)
        {
            StatusText = result.ErrorMessage ?? "Failed to cancel task.";
            return;
        }

        PendingApproval = null;
        StatusText = "Task canceled.";
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
                var maybePrompt = TryMapApprovalPrompt(timelineEvent);
                if (maybePrompt is not null)
                {
                    PendingApproval = maybePrompt;
                }
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

    private static ApprovalPromptViewModel? TryMapApprovalPrompt(TaskTimelineEvent timelineEvent)
    {
        if (timelineEvent.TaskStatus != TaskStatus.WaitingForApproval)
        {
            return null;
        }

        if (!timelineEvent.Detail.StartsWith("APPROVAL_REQUIRED", StringComparison.Ordinal))
        {
            return null;
        }

        var lines = timelineEvent.Detail.Split(Environment.NewLine, StringSplitOptions.RemoveEmptyEntries);
        var action = ReadApprovalLine(lines, "Action:") ?? timelineEvent.Title;
        var why = ReadApprovalLine(lines, "Why:") ?? "This action can impact your system or data.";
        var target = ReadApprovalLine(lines, "Target:") ?? "unknown target";
        var riskClass = ReadApprovalLine(lines, "Risk class:") ?? "write";

        return new ApprovalPromptViewModel
        {
            TaskId = timelineEvent.TaskId,
            StepId = timelineEvent.StepId,
            ActionSummary = action,
            Reason = why,
            Target = target,
            RiskClass = riskClass,
        };
    }

    private static string? ReadApprovalLine(IEnumerable<string> lines, string prefix)
    {
        foreach (var line in lines)
        {
            if (line.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                return line[prefix.Length..].Trim();
            }
        }

        return null;
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
