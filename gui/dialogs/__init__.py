# Import from legacy dialogs file directly to avoid circular imports since python has gui/dialogs folder as package
from gui.dialogs_legacy import GlobalSearchDialog, SmartCaptureDialog, PromoteIdeaToProjectDialog, PromoteIdeaToTaskDialog, UnresolvedLinkDialog
from gui.dialogs.alert_edit_dialog import AlertEditDialog