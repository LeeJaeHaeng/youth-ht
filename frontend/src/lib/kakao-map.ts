type KakaoStatus = "OK" | "ZERO_RESULT" | "ERROR";

type KakaoPlaceDocument = {
  id: string;
  place_name: string;
  address_name: string;
  road_address_name: string;
  x: string;
  y: string;
};

type KakaoLatLng = unknown;
type KakaoMap = {
  addControl: (control: unknown, position: unknown) => void;
  setBounds: (
    bounds: KakaoBounds,
    paddingTop?: number,
    paddingRight?: number,
    paddingBottom?: number,
    paddingLeft?: number,
  ) => void;
};
type KakaoBounds = {
  extend: (latLng: KakaoLatLng) => void;
  isEmpty: () => boolean;
};

type KakaoNamespace = {
  maps: {
    load: (callback: () => void) => void;
    LatLng: new (lat: number, lng: number) => KakaoLatLng;
    LatLngBounds: new () => KakaoBounds;
    Map: new (
      container: HTMLElement,
      options: {
        center: KakaoLatLng;
        level: number;
      },
    ) => KakaoMap;
    ZoomControl: new () => unknown;
    ControlPosition: {
      RIGHT: unknown;
    };
    CustomOverlay: new (options: {
      map: KakaoMap;
      position: KakaoLatLng;
      yAnchor?: number;
      content: string;
    }) => unknown;
    services: {
      Places: new () => {
        keywordSearch: (
          keyword: string,
          callback: (documents: KakaoPlaceDocument[], status: KakaoStatus) => void,
        ) => void;
      };
      Status: Record<KakaoStatus, KakaoStatus>;
    };
  };
};

export type KakaoPlace = {
  id: string;
  name: string;
  address: string;
  lat: number;
  lng: number;
};

declare global {
  interface Window {
    kakao?: KakaoNamespace;
  }
}

let kakaoLoadPromise: Promise<KakaoNamespace> | null = null;

export function getKakaoJsKey(): string {
  const key =
    (import.meta.env.VITE_KAKAO_JS_KEY as string | undefined) ??
    (import.meta.env.VITE_KAKAO_MAP_KEY as string | undefined) ??
    "";

  return key.trim();
}

export function loadKakaoMaps(): Promise<KakaoNamespace> {
  if (typeof window === "undefined")
    return Promise.reject(new Error("브라우저에서만 카카오맵을 사용할 수 있습니다."));
  if (window.kakao?.maps?.services) return Promise.resolve(window.kakao);
  if (kakaoLoadPromise) return kakaoLoadPromise;

  const appKey = getKakaoJsKey();
  if (!appKey) {
    return Promise.reject(new Error("VITE_KAKAO_JS_KEY가 설정되지 않았습니다."));
  }

  kakaoLoadPromise = new Promise<KakaoNamespace>((resolve, reject) => {
    const existing = document.getElementById("kakao-map-sdk") as HTMLScriptElement | null;
    const loadError = new Error(
      "카카오맵 SDK 로드 실패: JavaScript 키의 웹 플랫폼 도메인에 현재 주소를 등록해야 합니다.",
    );

    const onReady = () => {
      if (!window.kakao?.maps) {
        reject(new Error("카카오맵 SDK를 불러오지 못했습니다."));
        return;
      }
      window.kakao.maps.load(() => resolve(window.kakao as KakaoNamespace));
    };

    if (existing) {
      if (window.kakao?.maps) onReady();
      else existing.addEventListener("load", onReady, { once: true });
      existing.addEventListener("error", () => reject(loadError), {
        once: true,
      });
      return;
    }

    const script = document.createElement("script");
    script.id = "kakao-map-sdk";
    script.async = true;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${appKey}&autoload=false&libraries=services`;
    script.onload = onReady;
    script.onerror = () => reject(loadError);
    document.head.appendChild(script);
  }).catch((error) => {
    kakaoLoadPromise = null;
    throw error;
  });

  return kakaoLoadPromise;
}

export async function searchKakaoPlaces(query: string): Promise<KakaoPlace[]> {
  const keyword = query.trim();
  if (!keyword) return [];

  const kakao = await loadKakaoMaps();
  return new Promise((resolve, reject) => {
    const places = new kakao.maps.services.Places();
    places.keywordSearch(keyword, (documents: KakaoPlaceDocument[], status: KakaoStatus) => {
      if (status === kakao.maps.services.Status.OK) {
        resolve(
          documents.slice(0, 6).map((doc) => ({
            id: doc.id,
            name: doc.place_name,
            address: doc.road_address_name || doc.address_name,
            lat: Number(doc.y),
            lng: Number(doc.x),
          })),
        );
        return;
      }
      if (status === kakao.maps.services.Status.ZERO_RESULT) {
        resolve([]);
        return;
      }
      reject(new Error("카카오 장소 검색에 실패했습니다."));
    });
  });
}
