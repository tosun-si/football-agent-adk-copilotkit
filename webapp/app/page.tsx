"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { Header } from "@/components/Header";
import { chartTagRenderers } from "@/components/CopilotMarkdown";

export default function Home() {
  return (
    <div className="flex flex-col h-screen">
      <Header />
      <div className="flex-1 overflow-hidden">
        <CopilotChat
          className="h-full"
          labels={{
            title: "Football Stats Agent",
            initial:
              "Pose-moi une question sur la Coupe du monde 2022 — j'interroge BigQuery en langage naturel et je peux générer des graphes.",
            placeholder: "Ex. : Qui sont les 5 meilleurs buteurs de France ?",
          }}
          markdownTagRenderers={chartTagRenderers}
        />
      </div>
    </div>
  );
}
