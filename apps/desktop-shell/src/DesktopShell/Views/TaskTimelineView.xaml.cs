using DesktopShell.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace DesktopShell.Views;

public sealed partial class TaskTimelineView : UserControl
{
    public TaskTimelineViewModel ViewModel { get; }

    public TaskTimelineView()
    {
        var app = (App)Application.Current;
        ViewModel = app.TaskTimelineViewModel;
        InitializeComponent();
    }

    private async void StartTask_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        await ViewModel.StartTaskAsync();
    }
}
