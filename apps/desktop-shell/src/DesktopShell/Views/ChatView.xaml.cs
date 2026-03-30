using DesktopShell.Services;
using DesktopShell.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace DesktopShell.Views;

public sealed partial class ChatView : UserControl
{
    public ChatViewModel ViewModel { get; }

    public ChatView()
    {
        ViewModel = new ChatViewModel(new DaemonConnectionService());
        InitializeComponent();
    }

    private async void SendMessage_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        await ViewModel.SendMessageAsync();
    }
}
