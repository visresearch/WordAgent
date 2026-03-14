/*
 * Copyright (c) WenCe Team. All rights reserved. Licensed under the MIT license.
 */

/* global Office */

Office.onReady(() => {
  // If needed, Office.js is ready to be called.
});

/**
 * Shows a notification when the add-in command is executed.
 * @param event {Office.AddinCommands.Event}
 */
function action(event) {
  const message = {
    type: Office.MailboxEnums.ItemNotificationMessageType.InformationalMessage,
    message: "文策AI助手已执行操作。",
    icon: "Icon.80x80",
    persistent: true,
  };

  // Show a notification message.
  try {
    Office.context.mailbox.item.notificationMessages.replaceAsync("ActionPerformanceNotification", message);
  } catch (e) {
    // Not in mailbox context, ignore
  }

  // Be sure to indicate when the add-in command function is complete.
  event.completed();
}

// Register the function with Office.
Office.actions.associate("action", action);
