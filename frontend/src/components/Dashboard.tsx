import { ReactNode, useState } from "react";
import { Meta } from "../api";
import MissionControl from "./MissionControl";
import BanditPanel from "./BanditPanel";
import ModelCard from "./ModelCard";
import { Bolt, Dice, Shield } from "./Icons";

type InnerTab = "feed" | "bandit" | "model";

export default function Dashboard({ meta }: { meta: Meta | null }) {
  const [tab, setTab] = useState<InnerTab>("feed");
  const [refreshKey] = useState(0);

  return (
    <div>
      <div className="flex flex-wrap gap-1 mb-5 p-1 bg-card ring-1 ring-foreground/10 rounded-xl w-fit">
        {([
          ["feed", <Bolt key="b" size={14} />, "Live Agent Feed"],
          ["bandit", <Dice key="d" size={14} />, "Bandit & Trust"],
          ["model", <Shield key="s" size={14} />, "Model & Trust"],
        ] as [InnerTab, ReactNode, string][]).map(([key, icon, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`text-sm font-medium px-3.5 py-2 rounded-lg flex items-center gap-1.5 transition-colors ${
              tab === key
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-card-foreground hover:bg-muted/60"
            }`}
          >
            {icon} {label}
          </button>
        ))}
      </div>

      {tab === "feed" && <MissionControl meta={meta} />}
      {tab === "bandit" && <BanditPanel refreshKey={refreshKey} />}
      {tab === "model" && <ModelCard meta={meta} />}
    </div>
  );
}
