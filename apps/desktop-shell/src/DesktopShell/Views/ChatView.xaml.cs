using DesktopShell.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Windows.Storage.Pickers;

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

    private async void AddFolder_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        var app = (App)Application.Current;
        var picker = new FolderPicker();
        picker.FileTypeFilter.Add("*");

        var windowHandle = WinRT.Interop.WindowNative.GetWindowHandle(app.MainWindow);
        WinRT.Interop.InitializeWithWindow.Initialize(picker, windowHandle);

        var folder = await picker.PickSingleFolderAsync();
        if (folder is null)
        {
            return;
        }

        await ViewModel.AttachFolderAsync(folder.Path, WorkspaceAccessMode.ReadOnly);
        await app.SidebarViewModel.RefreshConversationsAsync();
    }
}
