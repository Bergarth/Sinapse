using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using DesktopShell.Services;

namespace DesktopShell.ViewModels;

public class MainWindowViewModel : INotifyPropertyChanged
{
    private readonly DaemonConnectionService _daemonConnectionService;

    private string _daemonStatus = "Checking daemon...";
    private string _daemonVersion = "-";
    private string _environmentStatus = "Checking environment...";
    private string _environmentName = "-";
    private string _connectionDetail = "Trying to contact the daemon during startup.";
    private string _lastSuccessfulConnection = "Never";
    private bool _isConnected;

    public MainWindowViewModel(DaemonConnectionService daemonConnectionService)
    {
        _daemonConnectionService = daemonConnectionService;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public string AppTitle { get; } = "Desktop Shell";

    public ObservableCollection<string> CapabilityStatuses { get; } =
    [
        "chat — checking...",
        "tasks — checking...",
        "workspaces — checking...",
        "windows operator — checking...",
    ];

    public string DaemonStatus
    {
        get => _daemonStatus;
        private set => SetProperty(ref _daemonStatus, value);
    }

    public string DaemonVersion
    {
        get => _daemonVersion;
        private set => SetProperty(ref _daemonVersion, value);
    }

    public string EnvironmentStatus
    {
        get => _environmentStatus;
        private set => SetProperty(ref _environmentStatus, value);
    }

    public string EnvironmentName
    {
        get => _environmentName;
        private set => SetProperty(ref _environmentName, value);
    }

    public string LastSuccessfulConnection
    {
        get => _lastSuccessfulConnection;
        private set => SetProperty(ref _lastSuccessfulConnection, value);
    }

    public string ConnectionDetail
    {
        get => _connectionDetail;
        private set => SetProperty(ref _connectionDetail, value);
    }

    public bool IsConnected
    {
        get => _isConnected;
        private set => SetProperty(ref _isConnected, value);
    }

    public string ConnectionIndicatorEmoji => IsConnected ? "🟢" : "🔴";

    public async Task RefreshConnectionStatusAsync(CancellationToken cancellationToken = default)
    {
        DaemonStatus = "Checking daemon...";
        EnvironmentStatus = "Checking environment...";
        ConnectionDetail = "Requesting startup status from daemon.";

        var result = await _daemonConnectionService.GetStartupStatusAsync(cancellationToken);

        IsConnected = result.IsConnected;
        DaemonStatus = result.DaemonStatus;
        DaemonVersion = result.DaemonVersion;
        EnvironmentStatus = result.EnvironmentStatus;
        EnvironmentName = result.EnvironmentName;
        ConnectionDetail = result.ErrorMessage ?? $"Connected to {result.Endpoint}";
        LastSuccessfulConnection = result.LastSuccessfulConnectionUtc?.ToLocalTime().ToString("u") ?? "Never";

        CapabilityStatuses.Clear();
        if (result.Capabilities.Count == 0)
        {
            CapabilityStatuses.Add("chat — unavailable");
            CapabilityStatuses.Add("tasks — unavailable");
            CapabilityStatuses.Add("workspaces — unavailable");
            CapabilityStatuses.Add("windows operator — unavailable");
        }
        else
        {
            foreach (var capability in result.Capabilities)
            {
                var availability = capability.IsAvailable ? "available" : "unavailable";
                CapabilityStatuses.Add($"{capability.CapabilityName} — {availability} ({capability.Detail})");
            }
        }

        OnPropertyChanged(nameof(ConnectionIndicatorEmoji));
    }

    private void SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return;
        }

        field = value;
        OnPropertyChanged(propertyName);
    }

    private void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
