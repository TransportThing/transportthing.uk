import React, { memo, useEffect, createContext } from "react";
import { createRoot } from "react-dom/client";
// import { captureException } from "@sentry/react";

import MapGL, {
  NavigationControl,
  GeolocateControl,
  AttributionControl,
  type MapProps,
  useControl,
  useMap,
  Popup,
  type LngLat,
  type MapLayerMouseEvent,
  type PopupEvent,
} from "react-map-gl/maplibre";

import arrow from "data-url:../history-arrow.png";
import routeStopMarkerCircle from "data-url:../route-stop-marker-circle.png";
import routeStopMarkerDarkCircle from "data-url:../route-stop-marker-dark-circle.png";
import routeStopMarkerDark from "data-url:../route-stop-marker-dark.png";
import routeStopMarker from "data-url:../route-stop-marker.png";
import stopMarkerCircle from "data-url:../stop-marker-circle.png";
import stopMarker from "data-url:../stop-marker.png";
import type {
  Map as MapLibreMap,
  MapStyleImageMissingEvent,
} from "maplibre-gl";

const THUNDERFOREST_API_KEY = "b39c71a7e47441c8819703265852cca5";
const MAPTILER_API_KEY = "55Ux4HYOATM9YGB8TSb9";

const imagesByName: { [imageName: string]: string } = {
  "stop-marker": stopMarker,
  "stop-marker-circle": stopMarkerCircle,
  "route-stop-marker": routeStopMarker,
  "route-stop-marker-circle": routeStopMarkerCircle,
  "route-stop-marker-dark": routeStopMarkerDark,
  "route-stop-marker-dark-circle": routeStopMarkerDarkCircle,
  "history-arrow": arrow,
};

// Updated mapStyles to only use timesbus.org styles
const mapStyles: { [key: string]: string } = {
  aws_light: "AWS Light",
  aws_dark: "AWS Dark",
  aws_mono_light: "AWS Light (Mono)",
  aws_mono_dark: "AWS Dark (Mono)",
  osm_bright: "OSM Bright",
  aws_satellite: "AWS Satellite",
};

type StyleSwitcherProps = {
  style: string;
  onChange: React.ChangeEventHandler<HTMLInputElement>;
};

class StyleSwitcher {
  style: string;
  handleChange: React.ChangeEventHandler<HTMLInputElement>;
  _container?: HTMLElement;

  constructor(props: StyleSwitcherProps) {
    this.style = props.style;
    this.handleChange = props.onChange;
  }

  onAdd() {
    this._container = document.createElement("div");

    const root = createRoot(this._container);
    root.render(
      <details className="maplibregl-ctrl maplibregl-ctrl-group map-style-switcher">
        <summary>Map style</summary>
        {Object.entries(mapStyles).map(([key, value]) => (
          <label key={key}>
            <input
              type="radio"
              value={key}
              name="map-style"
              defaultChecked={key === this.style}
              onChange={this.handleChange}
            />
            {value}
          </label>
        ))}
      </details>,
    );
    return this._container;
  }

  onRemove() {
    this._container?.parentNode?.removeChild(this._container);
  }
}

const StyleSwitcherControl = memo(function StyleSwitcherControl(
  props: StyleSwitcherProps,
) {
  useControl(() => new StyleSwitcher(props));

  return null;
});

export const ThemeContext = createContext("");

function MapChild({ onInit }: { onInit?: (map: MapLibreMap) => void }) {
  const { current: map } = useMap();

  useEffect(() => {
    if (map) {
      const _map = map.getMap();
      _map.keyboard.disableRotation();
      _map.touchZoomRotate.disableRotation();

      if (onInit) {
        onInit(_map);
      }

      const onStyleImageMissing = (e: MapStyleImageMissingEvent) => {
        if (e.id in imagesByName) {
          const image = new Image();
          image.src = imagesByName[e.id];
          image.onload = () => {
            if (!map.hasImage(e.id)) {
              map.addImage(e.id, image, {
                pixelRatio: 2,
              });
            }
          };
        }
      };

      map.on("styleimagemissing", onStyleImageMissing);

      return () => {
        map.off("styleimagemissing", onStyleImageMissing);
      };
    }
  });

  return null;
}

export default function BusTimesMap(
  props: MapProps & {
    onMapInit?: (map: MapLibreMap) => void;
  },
) {
  const darkModeQuery = window.matchMedia("(prefers-color-scheme: dark)");

  const [mapStyle, setMapStyle] = React.useState(() => {
    try {
      const style = localStorage.getItem("map-style");
      if (style && style in mapStyles) {
        return style;
      }
    } catch {
      // ignore
    }
    return darkModeQuery.matches
      ? "aws_dark"
      : "aws_light";
  });

  useEffect(() => {
    const handleChange = (e: MediaQueryListEvent) => {
      setMapStyle(
        e.matches ? "aws_dark" : "aws_light",
      );
    };

    darkModeQuery.addEventListener("change", handleChange);
    return () => {
      darkModeQuery.removeEventListener("change", handleChange);
    };
  }, [darkModeQuery]);

  const handleMapStyleChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const style = e.target.value;
      const defaultStyle = darkModeQuery.matches
        ? style === "aws_dark"
        : style === "aws_light";
      setMapStyle(style);
      try {
        if (style === defaultStyle) {
          localStorage.removeItem("map-style");
        } else {
          localStorage.setItem("map-style", style);
        }
      } catch {
        // ignore
      }
    },
    [darkModeQuery.matches],
  );

  const [contextMenu, setContextMenu] = React.useState<LngLat>();

  const onContextMenu = (e: MapLayerMouseEvent | PopupEvent) => {
    if ("lngLat" in e) {
      setContextMenu(e.lngLat);
    } else {
      setContextMenu(undefined);
    }
  };

  useEffect(() => {
    document.body.classList.toggle(
      "dark-mode",
      mapStyle.endsWith("_dark") ||
        (mapStyle === "aws_satellite" && darkModeQuery.matches),
    );
  }, [mapStyle, darkModeQuery.matches]);
  // Updated mapStyleURL logic
  let mapStyleURL: string;

  if (mapStyle === "aws_light") {
    mapStyleURL = "https://tiles.snubs.dev/styles/aws-light/style.json";
  } else if (mapStyle === "aws_dark") {
    mapStyleURL = "https://tiles.snubs.dev/styles/aws-dark/style.json";
  } else if (mapStyle === "aws_mono_light") {
    mapStyleURL = "https://tiles.snubs.dev/styles/aws-mono-light/style.json";
  } else if (mapStyle === "aws_mono_dark") {
    mapStyleURL = "https://tiles.snubs.dev/styles/aws-mono-dark/style.json";
  } else if (mapStyle === "aws_satellite") {
      mapStyleURL = `https://tiles.snubs.dev/styles/satellite/style.json`; 
  } else if (mapStyle === "osm_bright") {
      mapStyleURL = `https://tiles.snubs.dev/styles/bright/style.json`; 
  }
  else {
    console.warn(
      `Unknown map style: ${mapStyle}. Falling back to timesbus_bright.`,
    );
    mapStyleURL = "https://tiles.snubs.dev/styles/bright/style.json";
  }

  return (
    <ThemeContext.Provider value={mapStyle}>
      <MapGL
        {...props}
        reuseMaps
        crossSourceCollisions={false}
        touchPitch={false}
        pitchWithRotate={false}
        dragRotate={false}
        minZoom={2}
        maxZoom={18}
        projection={"globe"}
        mapStyle={mapStyleURL}
        RTLTextPlugin={""}
        attributionControl={false}
        // onError={(e) => captureException(e.error)}
        onContextMenu={onContextMenu}
      >
        <NavigationControl showCompass={false} />
        <GeolocateControl trackUserLocation />
        <StyleSwitcherControl
          style={mapStyle}
          onChange={handleMapStyleChange}
        />
        <AttributionControl />
        <MapChild onInit={props.onMapInit} />

        {props.children}
        {contextMenu ? (
          <Popup
            longitude={contextMenu.lng}
            latitude={contextMenu.lat}
            onClose={onContextMenu}
          >
            <a
              href={`https://www.openstreetmap.org/#map=15/${contextMenu.lat}/${contextMenu.lng}`}
              rel="noopener noreferrer"
            >
              OpenStreetMap
            </a>
            <a
              href={`https://www.google.com/maps/search/?api=1&query=${contextMenu.lat},${contextMenu.lng}`}
              rel="noopener noreferrer"
            >
              Google Maps
            </a>
          </Popup>
        ) : null}
      </MapGL>
    </ThemeContext.Provider>
  );
}
