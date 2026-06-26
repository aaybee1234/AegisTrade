import { BookOpen, Brain, LineChart, ShieldCheck } from "lucide-react";

const lessons = [
  {
    title: "Start With Demo Trading",
    icon: ShieldCheck,
    body: "Use a demo account until you understand spread, lot size, stop loss, take profit, and how fast positions can move."
  },
  {
    title: "Risk Comes First",
    icon: LineChart,
    body: "Before entering a trade, decide how much you can lose. A stop loss is not optional; it is the boundary of the idea."
  },
  {
    title: "AI Is A Filter",
    icon: Brain,
    body: "AI can veto, explain, and rank setups, but deterministic risk rules must approve every order before MT5 execution."
  },
  {
    title: "Keep A Journal",
    icon: BookOpen,
    body: "Track why a trade opened, what the risk was, why it closed, and what should change next time."
  }
];

export default function GuidePage() {
  return (
    <main className="guideShell">
      <header className="guideHero">
        <a href="/" className="backLink">Back to dashboard</a>
        <p className="eyebrow">Trading guide</p>
        <h1>Learn the basics before the bot scales up.</h1>
        <p>
          AegisTrade is demo-first. The goal is to understand trade setup quality, risk, execution, and journaling before trusting automation with larger decisions.
        </p>
      </header>

      <section className="guideGrid">
        {lessons.map((lesson) => {
          const Icon = lesson.icon;
          return (
            <article className="guideCard" key={lesson.title}>
              <Icon size={22} />
              <h2>{lesson.title}</h2>
              <p>{lesson.body}</p>
            </article>
          );
        })}
      </section>

      <section className="guideSection">
        <h2>Core Terms</h2>
        <div className="termGrid">
          <div><strong>Spread</strong><span>The difference between buy and sell price. High spread makes entries more expensive.</span></div>
          <div><strong>Lot Size</strong><span>The trade volume. A larger lot makes wins and losses move faster.</span></div>
          <div><strong>Stop Loss</strong><span>The price where the trade exits if the idea is wrong.</span></div>
          <div><strong>Take Profit</strong><span>The price where the trade exits if the target is reached.</span></div>
          <div><strong>Floating P/L</strong><span>The current unrealized profit or loss of open positions.</span></div>
          <div><strong>ATR</strong><span>A volatility measure. Wider markets need wider stops.</span></div>
        </div>
      </section>

      <section className="guideSection">
        <h2>How AegisTrade Decides</h2>
        <ol className="stepList">
          <li>Read live MT5 account, symbol, spread, and candle data.</li>
          <li>Create a strategy signal from trend and volatility.</li>
          <li>Ask the AI review agent to explain or veto the setup.</li>
          <li>Run deterministic risk checks.</li>
          <li>Send a demo order only if all gates pass.</li>
          <li>Show open positions and advisory notes in the dashboard.</li>
        </ol>
      </section>

      <section className="guideSection warningGuide">
        <h2>What Users Should Know</h2>
        <p>
          This is not a guaranteed-profit system. A stronger model can improve explanations and filtering, but it cannot remove market risk. The demo phase is where strategies should fail safely, get logged, and improve.
        </p>
      </section>
    </main>
  );
}
