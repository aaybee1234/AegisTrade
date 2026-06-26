export type TradeAction = "BUY" | "SELL" | "HOLD";

export type TradeSignal = {
  symbol: string;
  action: TradeAction;
  confidence: number;
  lotSize: number;
  entryType: "MARKET";
  stopLossPips: number;
  takeProfitPips: number;
  reason: string;
};

export type RiskDecision =
  | {
      approved: true;
      order: {
        symbol: string;
        action: Exclude<TradeAction, "HOLD">;
        lotSize: number;
        stopLoss: number;
        takeProfit: number;
      };
    }
  | {
      approved: false;
      reason: string;
    };

