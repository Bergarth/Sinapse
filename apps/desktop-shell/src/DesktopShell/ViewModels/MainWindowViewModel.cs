using System.ComponentModel;
using System.Runtime.CompilerServices;
using DesktopShell.Services;

namespace DesktopShell.ViewModels;

public class MainWindowViewModel : INotifyPropertyChanged
{
    private readonly DaemonConnectionService _daemonConnectionService;

    private string _connectionStatus = "Checking...";
    private string _connectionDetail = "Trying to contact the daemon during startup.";
    private bool _isConnected;

    public MainWindowViewModel(DaemonConnectionService daemonConnectionService)
    {
        _daemonConnectionService = daemonConnectionService;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public string AppTitle { get; } = "Desktop Shell";

    public string ConnectionStatus
    {
        get => _connectionStatus;
        private set => SetProperty(ref _connectionStatus, value);
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
        ConnectionStatus = "Checking...";
        ConnectionDetail = "Running a daemon health check from the shell.";

        var result = await _daemonConnectionService.CheckHealthAsync(cancellationToken);

        IsConnected = result.IsConnected;
        ConnectionStatus = result.StatusMessage;
        ConnectionDetail = result.ErrorMessage
            ?? $"Daemon is reachable at {result.Endpoint}.";

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
