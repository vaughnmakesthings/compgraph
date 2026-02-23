import { AppShell } from "@/components/app-shell";

function SettingField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="mb-1.5 text-[13px] text-muted-foreground">{label}</div>
      <div className="w-full rounded-md border border-border bg-muted/30 px-3 py-2 text-[13px]">
        {value}
      </div>
    </div>
  );
}

function SettingSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
      <h3 className="mb-4 font-display text-[14px] font-semibold">{title}</h3>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <AppShell title="Settings" subtitle="Configuration">
      <div className="space-y-6">
        <div className="rounded-md border border-border bg-muted/50 p-3 text-[13px] text-muted-foreground">
          Read-only during evaluation phase
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <SettingSection title="API Provider">
            <SettingField label="Provider" value="OpenRouter" />
            <SettingField label="API Key" value="••••••••" />
          </SettingSection>

          <SettingSection title="Models">
            <SettingField label="Pass 1 Model" value="haiku-3.5" />
            <SettingField label="Pass 2 Model" value="sonnet-4" />
          </SettingSection>

          <SettingSection title="Prompt Versions">
            <SettingField label="Pass 1 Prompt" value="pass1_v1" />
            <SettingField label="Pass 2 Prompt" value="pass2_v1" />
          </SettingSection>

          <SettingSection title="Defaults">
            <SettingField label="Concurrency" value="5" />
            <SettingField label="Corpus Size" value="50" />
          </SettingSection>
        </div>
      </div>
    </AppShell>
  );
}
