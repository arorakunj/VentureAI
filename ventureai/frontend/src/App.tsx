import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { LandingPage } from "@/components/LandingPage";
import { AppWorkspace } from "@/components/AppWorkspace";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/app" element={<AppWorkspace />} />
        <Route path="*" element={<LandingPage />} />
      </Routes>
    </Layout>
  );
}
