# desktop-shell

Beginner-friendly scaffold for a **WinUI 3 desktop shell** using an MVVM-oriented folder layout.

## What this includes

- `src/DesktopShell/DesktopShell.csproj`: WinUI 3 project file (placeholder dependencies).
- `App` + `MainWindow` bootstrap files.
- `Views/` placeholders for:
  - Main window composition
  - Chat view
  - Sidebar
  - Settings view
  - Onboarding view
  - Task timeline placeholder
  - Artifact panel placeholder
- `ViewModels/` placeholder classes matching each view.
- `Models/` and `Services/` folders with guidance notes.

## What this intentionally does **not** include

- No AI logic.
- No backend integration.
- No fake/mock service workflows.

## Suggested next steps

1. Add a `NavigationService` for moving between major views.
2. Add `INotifyPropertyChanged` base types for ViewModels.
3. Wire `SettingsView` and `OnboardingView` into explicit routes/dialogs.
4. Add unit tests for ViewModel behavior as logic appears.
