using DesktopShell.ViewModels;
using Microsoft.UI.Xaml.Controls;

namespace DesktopShell.Views;

public sealed partial class ChatView : UserControl
{
    public ChatViewModel ViewModel { get; } = new();

    public ChatView()
    {
        InitializeComponent();
    }
}
