using DesktopShell.Services;
using DesktopShell.ViewModels;
using Microsoft.UI.Xaml;

namespace DesktopShell;

public partial class App : Application
{
    public App()
    {
        InitializeComponent();
    }

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        var daemonConnectionService = new DaemonConnectionService();
        var mainWindowViewModel = new MainWindowViewModel(daemonConnectionService);
        var window = new MainWindow(mainWindowViewModel);
        window.Activate();

        await mainWindowViewModel.RefreshConnectionStatusAsync();
    }
}
