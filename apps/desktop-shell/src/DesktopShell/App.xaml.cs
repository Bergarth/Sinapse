using DesktopShell.ViewModels;
using Microsoft.UI.Xaml;

namespace DesktopShell;

public partial class App : Application
{
    public App()
    {
        InitializeComponent();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        var mainWindowViewModel = new MainWindowViewModel();
        var window = new MainWindow(mainWindowViewModel);
        window.Activate();
    }
}
