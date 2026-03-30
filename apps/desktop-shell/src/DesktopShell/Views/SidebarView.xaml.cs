using DesktopShell.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace DesktopShell.Views;

public sealed partial class SidebarView : UserControl
{
    public SidebarViewModel ViewModel { get; }

    public SidebarView()
    {
        var app = (App)Application.Current;
        ViewModel = app.SidebarViewModel;
        InitializeComponent();
    }

    private async void Refresh_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        await ViewModel.RefreshConversationsAsync();
    }

    private void ConversationList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        _ = e;
        if (sender is not ListView listView || listView.SelectedItem is not ConversationSummaryViewModel selectedConversation)
        {
            return;
        }

        ViewModel.SelectConversation(selectedConversation.ConversationId);
    }
}
