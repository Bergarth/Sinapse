using DesktopShell.Services;
using DesktopShell.ViewModels;
using Microsoft.UI.Dispatching;
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
    public SettingsViewModel SettingsViewModel { get; private set; } = null!;
    public TaskTimelineViewModel TaskTimelineViewModel { get; private set; } = null!;
    public MainWindow MainWindow { get; private set; } = null!;

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        _ = args;

        ChatViewModel = new ChatViewModel(DaemonConnectionService);
        SidebarViewModel = new SidebarViewModel(DaemonConnectionService);
        SettingsViewModel = new SettingsViewModel(DaemonConnectionService);
        TaskTimelineViewModel = new TaskTimelineViewModel(
            DaemonConnectionService,
            DispatcherQueue.GetForCurrentThread()!);

        ChatViewModel.ConversationChanged += (_, conversationId) => SidebarViewModel.MarkSelectedConversation(conversationId);
        ChatViewModel.ConversationChanged += (_, conversationId) => TaskTimelineViewModel.SetConversationId(conversationId);
        SidebarViewModel.ConversationSelected += async (_, conversationId) => await ChatViewModel.LoadConversationAsync(conversationId);
        SidebarViewModel.ConversationSelected += (_, conversationId) => TaskTimelineViewModel.SetConversationId(conversationId);

        var mainWindowViewModel = new MainWindowViewModel(DaemonConnectionService);
        MainWindow = new MainWindow(mainWindowViewModel);
        MainWindow.Activate();

        await mainWindowViewModel.RefreshConnectionStatusAsync();
        await SidebarViewModel.RefreshConversationsAsync();
        _ = TaskTimelineViewModel.BeginObservingAsync();
    }
}
