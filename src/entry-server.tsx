import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import App from "./App";
import { PreloadContext, Preload } from "./lib/preload";

export function render(url: string, preload: Preload, basename: string): string {
  return renderToString(
    <PreloadContext.Provider value={preload}>
      <StaticRouter location={url} basename={basename}>
        <App router={false} />
      </StaticRouter>
    </PreloadContext.Provider>
  );
}
