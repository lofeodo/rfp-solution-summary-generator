import { Link, Route, Routes } from "react-router-dom";
import Home from "./views/Home";
import RunPage from "./views/RunPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/runs/:id/:tab?" element={<RunPage />} />
      <Route
        path="*"
        element={
          <main className="mx-auto max-w-screen-2xl px-4 py-16 md:px-10">
            <p className="display text-6xl">Not here.</p>
            <Link to="/" className="btn mt-8">
              ← All runs
            </Link>
          </main>
        }
      />
    </Routes>
  );
}
