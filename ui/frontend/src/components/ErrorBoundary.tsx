import { Component, type ReactNode } from "react";

// A render error in one view shows a message instead of blanking the whole app.
export default class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidUpdate(prev: { resetKey?: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="border-l-4 border-accent bg-accentsoft px-4 py-3" role="alert">
        <p className="kicker text-accent">This view failed to render</p>
        <p className="mt-1 font-mono text-xs">{this.state.error.message}</p>
      </div>
    );
  }
}
