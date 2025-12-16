import React, { useEffect, useRef } from 'react';

const ForexNews = () => {
  const container = useRef();

  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-timeline.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = `
      {
        "feedMode": "market",
        "market": "forex",
        "isTransparent": true,
        "displayMode": "regular",
        "width": "100%",
        "height": "500",
        "colorTheme": "dark",
        "locale": "en"
      }`;
    container.current.appendChild(script);

    return () => {
        if(container.current) container.current.innerHTML = '';
    };
  }, []);

  return (
    <div className="tradingview-widget-container border border-slate-800 rounded-2xl p-4 bg-slate-900/50" ref={container}>
      <div className="tradingview-widget-container__widget"></div>
    </div>
  );
};

export default ForexNews;