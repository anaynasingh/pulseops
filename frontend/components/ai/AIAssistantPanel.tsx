"use client";

import { useUIStore } from "@/lib/store";
import { AssistantChat } from "@/components/ai/AssistantChat";

/**
 * Slide-in side panel wrapper around the shared AssistantChat. The full-page
 * version lives at /assistant and renders the same AssistantChat with variant="page".
 */
export function AIAssistantPanel() {
  const { toggleAIAssistant } = useUIStore();
  return (
    <div className="fixed right-0 top-0 bottom-0 w-80 border-l border-slate-800 z-20 shadow-2xl">
      <AssistantChat variant="panel" onClose={toggleAIAssistant} />
    </div>
  );
}
