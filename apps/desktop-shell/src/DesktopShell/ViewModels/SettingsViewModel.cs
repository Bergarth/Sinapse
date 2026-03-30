using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using DesktopShell.Services;
using Sinapse.Contracts.V1;

namespace DesktopShell.ViewModels;

public sealed class ProviderItemViewModel
{
    public required string ProviderId { get; init; }
    public required string DisplayName { get; init; }
}

public sealed class ApiKeyEntryItemViewModel
{
    public required string EntryId { get; init; }
    public required string ProviderId { get; init; }
    public required string DisplayName { get; init; }
    public required string PlaceholderRef { get; init; }
    public required string CreatedAt { get; init; }
}

public class SettingsViewModel : INotifyPropertyChanged
{
    private readonly DaemonConnectionService _daemonConnectionService;

    private ModelMode _selectedModelMode = ModelMode.Guided;
    private ProviderPreference _selectedProviderPreference = ProviderPreference.LocalPreferred;
    private string _newProviderName = string.Empty;
    private string _newApiKeyLabel = string.Empty;
    private string _selectedProviderIdForApiKey = string.Empty;
    private ProviderItemViewModel? _selectedProvider;
    private ApiKeyEntryItemViewModel? _selectedApiKeyEntry;
    private string _statusMessage = "Load settings to start configuring providers.";
    private bool _isSearchEnabled;
    private string _searchProviderId = "duckduckgo";
    private string _searchEndpoint = "https://api.duckduckgo.com/";
    private string _searchApiKeyPlaceholderRef = string.Empty;
    private bool _spokenRepliesEnabled;

    public SettingsViewModel(DaemonConnectionService daemonConnectionService)
    {
        _daemonConnectionService = daemonConnectionService;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public ObservableCollection<ProviderItemViewModel> Providers { get; } = [];

    public ObservableCollection<ApiKeyEntryItemViewModel> ApiKeyEntries { get; } = [];

    public IEnumerable<ModelMode> ModelModes { get; } = [ModelMode.Guided, ModelMode.Manual];

    public IEnumerable<ProviderPreference> ProviderPreferences { get; } = [
        ProviderPreference.LocalPreferred,
        ProviderPreference.CloudPreferred,
    ];

    public ModelMode SelectedModelMode
    {
        get => _selectedModelMode;
        set => SetProperty(ref _selectedModelMode, value);
    }

    public ProviderPreference SelectedProviderPreference
    {
        get => _selectedProviderPreference;
        set => SetProperty(ref _selectedProviderPreference, value);
    }

    public string NewProviderName
    {
        get => _newProviderName;
        set => SetProperty(ref _newProviderName, value);
    }

    public string NewApiKeyLabel
    {
        get => _newApiKeyLabel;
        set => SetProperty(ref _newApiKeyLabel, value);
    }

    public string SelectedProviderIdForApiKey
    {
        get => _selectedProviderIdForApiKey;
        set => SetProperty(ref _selectedProviderIdForApiKey, value);
    }

    public ProviderItemViewModel? SelectedProvider
    {
        get => _selectedProvider;
        set => SetProperty(ref _selectedProvider, value);
    }

    public ApiKeyEntryItemViewModel? SelectedApiKeyEntry
    {
        get => _selectedApiKeyEntry;
        set => SetProperty(ref _selectedApiKeyEntry, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public bool IsSearchEnabled
    {
        get => _isSearchEnabled;
        set => SetProperty(ref _isSearchEnabled, value);
    }

    public string SearchProviderId
    {
        get => _searchProviderId;
        set => SetProperty(ref _searchProviderId, value);
    }

    public string SearchEndpoint
    {
        get => _searchEndpoint;
        set => SetProperty(ref _searchEndpoint, value);
    }

    public string SearchApiKeyPlaceholderRef
    {
        get => _searchApiKeyPlaceholderRef;
        set => SetProperty(ref _searchApiKeyPlaceholderRef, value);
    }

    public bool SpokenRepliesEnabled
    {
        get => _spokenRepliesEnabled;
        set => SetProperty(ref _spokenRepliesEnabled, value);
    }

    public async Task LoadAsync(CancellationToken cancellationToken = default)
    {
        var result = await _daemonConnectionService.GetAppSettingsAsync(cancellationToken);
        if (!result.IsSuccess || result.Settings is null)
        {
            StatusMessage = result.ErrorMessage ?? "Could not load settings.";
            return;
        }

        HydrateFromDto(result.Settings);
        StatusMessage = "Settings loaded. You can safely edit placeholders and save.";
    }

    public void AddProvider()
    {
        var displayName = NewProviderName.Trim();
        if (string.IsNullOrWhiteSpace(displayName))
        {
            StatusMessage = "Please enter a provider name first (for example: OpenAI, Ollama, Anthropic).";
            return;
        }

        var providerId = ToProviderId(displayName);
        if (Providers.Any(provider => provider.ProviderId.Equals(providerId, StringComparison.OrdinalIgnoreCase)))
        {
            StatusMessage = $"A provider with ID '{providerId}' already exists.";
            return;
        }

        Providers.Add(new ProviderItemViewModel { ProviderId = providerId, DisplayName = displayName });
        SelectedProviderIdForApiKey = providerId;
        NewProviderName = string.Empty;
        StatusMessage = $"Added provider '{displayName}'.";
    }

    public void RemoveSelectedProvider()
    {
        if (SelectedProvider is null)
        {
            StatusMessage = "Select a provider to remove.";
            return;
        }

        var providerId = SelectedProvider.ProviderId;
        var linkedEntries = ApiKeyEntries.Where(entry => entry.ProviderId == providerId).ToList();
        foreach (var entry in linkedEntries)
        {
            ApiKeyEntries.Remove(entry);
        }

        Providers.Remove(SelectedProvider);
        SelectedProvider = null;
        StatusMessage = $"Removed provider '{providerId}' and {linkedEntries.Count} linked API key placeholder(s).";
    }

    public void AddApiKeyPlaceholder()
    {
        var providerId = SelectedProviderIdForApiKey.Trim();
        if (string.IsNullOrWhiteSpace(providerId) || !Providers.Any(provider => provider.ProviderId == providerId))
        {
            StatusMessage = "Choose an existing provider before adding an API key placeholder.";
            return;
        }

        var label = NewApiKeyLabel.Trim();
        if (string.IsNullOrWhiteSpace(label))
        {
            StatusMessage = "Please add a short label so you can recognize this API key placeholder later.";
            return;
        }

        var entryId = $"key-{Guid.NewGuid():N}";
        ApiKeyEntries.Add(
            new ApiKeyEntryItemViewModel
            {
                EntryId = entryId,
                ProviderId = providerId,
                DisplayName = label,
                PlaceholderRef = $"placeholder://{providerId}/{entryId}",
                CreatedAt = DateTimeOffset.UtcNow.ToString("O"),
            });

        NewApiKeyLabel = string.Empty;
        StatusMessage = "Added API key placeholder entry (no secret was saved).";
    }

    public void RemoveSelectedApiKeyPlaceholder()
    {
        if (SelectedApiKeyEntry is null)
        {
            StatusMessage = "Select an API key placeholder to remove.";
            return;
        }

        ApiKeyEntries.Remove(SelectedApiKeyEntry);
        SelectedApiKeyEntry = null;
        StatusMessage = "Removed API key placeholder entry.";
    }

    public async Task SaveAsync(CancellationToken cancellationToken = default)
    {
        if (Providers.Count == 0)
        {
            StatusMessage = "Add at least one provider before saving settings.";
            return;
        }

        var dto = new AppSettingsDto
        {
            ModelMode = SelectedModelMode,
            ProviderPreference = SelectedProviderPreference,
            SearchSettings = new SearchSettingsDto
            {
                Enabled = IsSearchEnabled,
                ProviderId = SearchProviderId.Trim(),
                Endpoint = SearchEndpoint.Trim(),
                ApiKeyPlaceholderRef = SearchApiKeyPlaceholderRef.Trim(),
            },
            SpeechSettings = new SpeechSettingsDto
            {
                SpokenRepliesEnabled = SpokenRepliesEnabled,
                SttProviderId = "local-whisper",
                TtsProviderId = "local-pyttsx3",
            },
        };

        dto.Providers.AddRange(Providers.Select(provider => new ProviderConfigDto
        {
            ProviderId = provider.ProviderId,
            DisplayName = provider.DisplayName,
        }));

        dto.ApiKeyEntries.AddRange(ApiKeyEntries.Select(entry => new ApiKeyEntryDto
        {
            EntryId = entry.EntryId,
            ProviderId = entry.ProviderId,
            DisplayName = entry.DisplayName,
            PlaceholderRef = entry.PlaceholderRef,
            CreatedAt = entry.CreatedAt,
        }));

        var result = await _daemonConnectionService.UpdateAppSettingsAsync(dto, cancellationToken);
        if (!result.IsSuccess || result.Settings is null)
        {
            StatusMessage = result.ErrorMessage ?? "Could not save settings.";
            return;
        }

        HydrateFromDto(result.Settings);
        StatusMessage = "Saved settings successfully.";
    }

    private void HydrateFromDto(AppSettingsDto settings)
    {
        SelectedModelMode = settings.ModelMode;
        SelectedProviderPreference = settings.ProviderPreference;
        IsSearchEnabled = settings.SearchSettings?.Enabled ?? false;
        SearchProviderId = string.IsNullOrWhiteSpace(settings.SearchSettings?.ProviderId)
            ? "duckduckgo"
            : settings.SearchSettings.ProviderId;
        SearchEndpoint = string.IsNullOrWhiteSpace(settings.SearchSettings?.Endpoint)
            ? "https://api.duckduckgo.com/"
            : settings.SearchSettings.Endpoint;
        SearchApiKeyPlaceholderRef = settings.SearchSettings?.ApiKeyPlaceholderRef ?? string.Empty;
        SpokenRepliesEnabled = settings.SpeechSettings?.SpokenRepliesEnabled ?? false;

        Providers.Clear();
        foreach (var provider in settings.Providers)
        {
            Providers.Add(new ProviderItemViewModel
            {
                ProviderId = provider.ProviderId,
                DisplayName = provider.DisplayName,
            });
        }

        ApiKeyEntries.Clear();
        foreach (var entry in settings.ApiKeyEntries)
        {
            ApiKeyEntries.Add(new ApiKeyEntryItemViewModel
            {
                EntryId = entry.EntryId,
                ProviderId = entry.ProviderId,
                DisplayName = entry.DisplayName,
                PlaceholderRef = entry.PlaceholderRef,
                CreatedAt = entry.CreatedAt,
            });
        }

        if (Providers.Count > 0 && string.IsNullOrWhiteSpace(SelectedProviderIdForApiKey))
        {
            SelectedProviderIdForApiKey = Providers[0].ProviderId;
        }
    }

    private static string ToProviderId(string displayName)
    {
        var chars = displayName
            .ToLowerInvariant()
            .Select(character => char.IsLetterOrDigit(character) ? character : '-')
            .ToArray();
        var normalized = new string(chars).Trim('-');

        while (normalized.Contains("--", StringComparison.Ordinal))
        {
            normalized = normalized.Replace("--", "-", StringComparison.Ordinal);
        }

        return string.IsNullOrWhiteSpace(normalized) ? $"provider-{Guid.NewGuid():N}" : normalized;
    }

    private bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return false;
        }

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }
}
