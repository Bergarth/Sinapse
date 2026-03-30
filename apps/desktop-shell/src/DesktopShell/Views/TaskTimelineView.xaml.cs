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

    private async void StartRiskyTask_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        await ViewModel.StartRiskyDemoTaskAsync();
    }

    private async void Approve_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        await ViewModel.ApprovePendingStepAsync();
    }

    private async void Deny_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        await ViewModel.DenyPendingStepAsync();
    }

    private async void CancelTask_Click(object sender, RoutedEventArgs e)
    {
        _ = sender;
        await ViewModel.CancelPendingTaskAsync();
    }
}
