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

    public DaemonConnectionService DaemonConnectionService { get; } = new();

    public ChatViewModel ChatViewModel { get; private set; } = null!;

    public SidebarViewModel SidebarViewModel { get; private set; } = null!;

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        _ = args;

        ChatViewModel = new ChatViewModel(DaemonConnectionService);
        SidebarViewModel = new SidebarViewModel(DaemonConnectionService);

        ChatViewModel.ConversationChanged += (_, conversationId) => SidebarViewModel.MarkSelectedConversation(conversationId);
        SidebarViewModel.ConversationSelected += async (_, conversationId) => await ChatViewModel.LoadConversationAsync(conversationId);

        var mainWindowViewModel = new MainWindowViewModel(DaemonConnectionService);
        var window = new MainWindow(mainWindowViewModel);
        window.Activate();

        await mainWindowViewModel.RefreshConnectionStatusAsync();
        await SidebarViewModel.RefreshConversationsAsync();
    }
}
