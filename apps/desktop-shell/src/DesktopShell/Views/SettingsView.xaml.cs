using DesktopShell.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Sinapse.Contracts.V1;

namespace DesktopShell.Views;

public sealed partial class SettingsView : UserControl
{
    private bool _initialized;

    public SettingsViewModel ViewModel { get; }

    public SettingsView()
    {
        var app = (App)Application.Current;
        ViewModel = app.SettingsViewModel;
        InitializeComponent();
        Loaded += SettingsView_Loaded;
    }

    private async void SettingsView_Loaded(object sender, RoutedEventArgs e)
    {
        _ = (sender, e);
        if (_initialized)
        {
            return;
        }

        await ViewModel.LoadAsync();
        SyncComboBoxesFromViewModel();
        _initialized = true;
    }

    private async void Reload_Click(object sender, RoutedEventArgs e)
    {
        _ = (sender, e);
        await ViewModel.LoadAsync();
        SyncComboBoxesFromViewModel();
    }

    private async void Save_Click(object sender, RoutedEventArgs e)
    {
        _ = (sender, e);
        ApplyComboBoxesToViewModel();
        await ViewModel.SaveAsync();
    }

    private void AddProvider_Click(object sender, RoutedEventArgs e)
    {
        _ = (sender, e);
        ViewModel.AddProvider();
    }

    private void RemoveProvider_Click(object sender, RoutedEventArgs e)
    {
        _ = (sender, e);
        ViewModel.RemoveSelectedProvider();
    }

    private void AddApiKeyPlaceholder_Click(object sender, RoutedEventArgs e)
    {
        _ = (sender, e);
        ViewModel.AddApiKeyPlaceholder();
    }

    private void RemoveApiKeyPlaceholder_Click(object sender, RoutedEventArgs e)
    {
        _ = (sender, e);
        ViewModel.RemoveSelectedApiKeyPlaceholder();
    }

    private void ProvidersList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        _ = e;
        ViewModel.SelectedProvider = (sender as ListView)?.SelectedItem as ProviderItemViewModel;
    }

    private void ApiKeysList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        _ = e;
        ViewModel.SelectedApiKeyEntry = (sender as ListView)?.SelectedItem as ApiKeyEntryItemViewModel;
    }

    private void SyncComboBoxesFromViewModel()
    {
        ModelModeComboBox.SelectedIndex = ViewModel.SelectedModelMode == ModelMode.Manual ? 1 : 0;
        PreferenceComboBox.SelectedIndex = ViewModel.SelectedProviderPreference == ProviderPreference.CloudPreferred ? 1 : 0;
    }

    private void ApplyComboBoxesToViewModel()
    {
        ViewModel.SelectedModelMode = ModelModeComboBox.SelectedIndex == 1 ? ModelMode.Manual : ModelMode.Guided;
        ViewModel.SelectedProviderPreference = PreferenceComboBox.SelectedIndex == 1
            ? ProviderPreference.CloudPreferred
            : ProviderPreference.LocalPreferred;
    }
}
