import Sidebar from "@/components/Sidebar";
import ChatArea from "@/components/ChatArea";

export default function Index({ vaultStatus, setVaultStatus }) {
  return (
    <div className="flex min-h-screen w-full">
      <Sidebar
        vaultStatus={vaultStatus}
        setVaultStatus={setVaultStatus}
      />
      <main className="flex-1">
        <ChatArea />
      </main>
    </div>
  );
}
