import Header from "../../components/layout/Header";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-screen-2xl">
      <Header />
      <div className="px-6 py-6">{children}</div>
    </div>
  );
}