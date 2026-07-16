"use client";

import { AssistantChat } from "@/components/ai/AssistantChat";

// Full-page AI Assistant — same functionality as the slide-in panel, roomier UI.
export default function AssistantPage() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <AssistantChat variant="page" />
    </div>
  );
}
