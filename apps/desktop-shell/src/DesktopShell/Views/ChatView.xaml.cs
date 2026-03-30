using DesktopShell.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace DesktopShell.Views;

public sealed partial class ChatView : UserControl
{
    public ChatViewModel ViewModel { get; }

    public ChatView()
    {
        var app = (App)Application.Current;
        ViewModel = app.ChatViewModel;
        InitializeComponent();
    }

    private async void SendMessage_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        await ViewModel.SendMessageAsync();

        var app = (App)Application.Current;
        await app.SidebarViewModel.RefreshConversationsAsync();
    }
}
