import React from 'react';
import { LayoutDashboard, Target, Info, RefreshCcw } from 'lucide-react';

interface SidebarProps {
  viewMode: 'scanner' | 'simulator';
  setViewMode: (mode: 'scanner' | 'simulator') => void;
  onRefresh: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ viewMode, setViewMode, onRefresh }) => {
  return (
    <div className="w-64 h-screen bg-[#0e1015] border-r border-[var(--border-color)] flex flex-col p-6 fixed">
      <div className="mb-10">
        <h2 className="text-xl font-bold bg-gradient-to-r from-white to-gray-500 bg-clip-text text-transparent">
          TERMINAL
        </h2>
        <p className="text-[10px] font-mono text-[var(--accent-green)] opacity-80 mt-1">
          STATISTICAL OPTIMIZATION
        </p>
      </div>

      <nav className="flex-1 space-y-2">
        <button
          onClick={() => setViewMode('scanner')}
          className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
            viewMode === 'scanner' 
              ? 'bg-[var(--accent-glow)] text-[var(--accent-green)] border border-[rgba(0,255,128,0.2)]' 
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <LayoutDashboard size={20} />
          <span className="font-semibold text-sm">Scanner Terminal</span>
        </button>

        <button
          onClick={() => setViewMode('simulator')}
          className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
            viewMode === 'simulator' 
              ? 'bg-[var(--accent-glow)] text-[var(--accent-green)] border border-[rgba(0,255,128,0.2)]' 
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Target size={20} />
          <span className="font-semibold text-sm">Custom Simulator</span>
        </button>
      </nav>

      <div className="mt-auto space-y-4">
        <button 
          onClick={onRefresh}
          className="w-full flex items-center justify-center space-x-2 bg-[var(--accent-green)] text-black font-bold py-3 rounded-lg hover:shadow-[0_0_15px_rgba(0,255,128,0.4)] transition-all active:scale-95"
        >
          <RefreshCcw size={18} />
          <span>FORCE REFRESH</span>
        </button>

        <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-[11px] text-gray-400 leading-relaxed">
          <div className="flex items-center space-x-2 mb-2 text-gray-300 font-bold uppercase tracking-wider">
            <Info size={12} />
            <span>Glossary</span>
          </div>
          <p><b className="text-gray-200">Alpha Score:</b> Weighted prob. index (0-1).</p>
          <p><b className="text-gray-200">P(Target):</b> Prob. of +15% return.</p>
          <p><b className="text-gray-200">Vol Edge:</b> HV minus IV Premium.</p>
          <p><b className="text-gray-200">Max Pain:</b> Price magnet strike.</p>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
