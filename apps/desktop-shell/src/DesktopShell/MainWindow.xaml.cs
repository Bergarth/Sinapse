using DesktopShell.ViewModels;
using Microsoft.UI.Xaml;

namespace DesktopShell;

public sealed partial class MainWindow : Window
{
    public MainWindowViewModel ViewModel { get; }

    public MainWindow(MainWindowViewModel viewModel)
    {
        ViewModel = viewModel;
        InitializeComponent();
    }

    private async void RetryConnectionCheck_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        await ViewModel.RefreshConnectionStatusAsync();
    }
}
