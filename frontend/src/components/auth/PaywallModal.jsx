import { X } from 'lucide-react';
import api from '../../services/api';

const PLANS = [
  { name: 'Investor', price: '£99/mo', annual: '£990/yr', priceId: process.env.REACT_APP_STRIPE_INVESTOR_PRICE_ID },
  { name: 'Auction House', price: '£55/mo', annual: '£550/yr', priceId: process.env.REACT_APP_STRIPE_AUCTION_PRICE_ID },
  { name: 'Deal Source', price: '£55/mo', annual: '£550/yr', priceId: process.env.REACT_APP_STRIPE_DEAL_PRICE_ID },
];

export default function PaywallModal({ onClose }) {
  const handleCheckout = async (priceId) => {
    try {
      const res = await api.post('/api/billing/create-checkout-session', {
        price_id: priceId,
        billing_period: 'monthly',
      });
      window.location.href = res.data.checkout_url;
    } catch (err) {
      console.error('Checkout failed:', err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Upgrade to continue</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={20} /></button>
        </div>
        <p className="text-slate-400 mb-6">You've used all your free views. Choose a plan to unlock full access.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PLANS.map(plan => (
            <div key={plan.name} className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
              <h3 className="text-white font-semibold mb-1">{plan.name}</h3>
              <p className="text-emerald-400 text-2xl font-bold mb-1">{plan.price}</p>
              <p className="text-slate-500 text-xs mb-4">or {plan.annual}</p>
              <button
                onClick={() => handleCheckout(plan.priceId)}
                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg py-2 text-sm font-medium transition-colors"
              >
                Subscribe
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
