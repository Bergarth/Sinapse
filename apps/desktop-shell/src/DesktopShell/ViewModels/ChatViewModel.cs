namespace DesktopShell.ViewModels;

public enum WorkspaceAccessMode
{
    ReadOnly,
    ReadWrite,
}

public sealed class WorkspaceRootViewModel
{
    public required string DisplayName { get; init; }

    public required string RootPath { get; init; }
}

public class ChatViewModel
{
    public string WorkspaceAttachmentTitle { get; } = "Attach folders to this conversation";

    public string WorkspaceAttachmentHelpText { get; } = "Add one or more folders to help the assistant understand your project context. You can start with a single folder and add more later.";

    public IReadOnlyList<WorkspaceRootViewModel> AttachedWorkspaceRoots { get; } =
    [
        new WorkspaceRootViewModel
        {
            DisplayName = "No folders attached yet",
            RootPath = "Choose a folder to display its root path here.",
        },
    ];

    public WorkspaceAccessMode SelectedAccessMode { get; } = WorkspaceAccessMode.ReadOnly;

    public string WorkspaceModeLabel => SelectedAccessMode == WorkspaceAccessMode.ReadOnly
        ? "Read-only workspace"
        : "Read-write workspace";

    public string WorkspaceModeDescription => SelectedAccessMode == WorkspaceAccessMode.ReadOnly
        ? "Recommended for first-time setup. The assistant can inspect files but cannot change them."
        : "Allows file edits after explicit confirmation flow is implemented.";

    public string WorkspaceRootDisplayTitle { get; } = "Visible workspace roots";

    public string WorkspaceRootDisplayDescription { get; } = "Attached folder roots appear here so you can confirm exactly what the assistant can access.";

    public string AddFolderButtonLabel { get; } = "Add folder (coming soon)";
}
