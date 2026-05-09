import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Tag } from '../components';
import { colors, font, radius, shadow, spacing } from '../theme';
import type { RecommendItem, RecommendRequest } from '../types';

// react-native-webview는 native(iOS/Android)에서만 사용
const WebView = Platform.OS !== 'web'
  ? require('react-native-webview').default
  : null;

interface Props {
  items: RecommendItem[];
  request: RecommendRequest;
  onCardPress: (item: RecommendItem) => void;
}

const RANK_COLORS = ['#DA7756', '#7C3AED', '#2D7A4F', '#B45309', '#1D4ED8'];

function buildMapHtml(
  items: RecommendItem[],
  workLat: number,
  workLng: number,
  jsKey: string,
): string {
  const markers = items
    .filter(it => it.lat && it.lng)
    .map(it => ({
      rank: it.rank,
      lat: it.lat,
      lng: it.lng,
      name: it.region_name,
      rent: Math.round(it.rent_mean_won / 10000),
      score: it.total_score.toFixed(0),
      color: RANK_COLORS[(it.rank - 1) % RANK_COLORS.length],
    }));

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"/>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html, body, #map { width:100%; height:100%; }
</style>
</head>
<body>
<div id="map"></div>
<script type="text/javascript"
  src="//dapi.kakao.com/v2/maps/sdk.js?appkey=${jsKey}&autoload=false">
</script>
<script>
function postMsg(data) {
  if (window.ReactNativeWebView) {
    window.ReactNativeWebView.postMessage(data);
  } else {
    window.parent.postMessage(data, '*');
  }
}
kakao.maps.load(function() {
  var map = new kakao.maps.Map(document.getElementById('map'), {
    center: new kakao.maps.LatLng(${workLat}, ${workLng}),
    level: 8
  });

  new kakao.maps.CustomOverlay({
    map: map,
    position: new kakao.maps.LatLng(${workLat}, ${workLng}),
    content: '<div style="background:#DA7756;color:#fff;padding:4px 8px;border-radius:12px;font-size:11px;font-weight:700;white-space:nowrap;margin-bottom:6px;">★ 직장</div>',
    yAnchor: 2.2
  });

  var markers = ${JSON.stringify(markers)};
  markers.forEach(function(m) {
    var pos = new kakao.maps.LatLng(m.lat, m.lng);
    var content = [
      '<div onclick="postMsg(JSON.stringify({rank:' + m.rank + '}))" ',
      'style="cursor:pointer;text-align:center;">',
      '<div style="background:' + m.color + ';color:#fff;width:32px;height:32px;border-radius:50%;',
      'display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;',
      'border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.25);">' + m.rank + '</div>',
      '<div style="background:rgba(255,255,255,0.95);border-radius:8px;padding:3px 6px;margin-top:3px;',
      'font-size:10px;font-weight:600;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,0.15);">',
      m.name.replace(/^.*?시\s|^.*?도\s/, '') + '<br/>' + m.rent + '만',
      '</div></div>'
    ].join('');
    new kakao.maps.CustomOverlay({
      map: map,
      position: pos,
      content: content,
      yAnchor: 1.0
    });
  });
});
</script>
</body>
</html>`;
}

export default function MapScreen({ items, request, onCardPress }: Props) {
  const KAKAO_JS_KEY = '262be337aa8ba19f321137cc4f087dcd';
  const [selectedItem, setSelectedItem] = useState<RecommendItem | null>(null);
  const slideAnim = useRef(new Animated.Value(200)).current;

  function showCard(item: RecommendItem) {
    setSelectedItem(item);
    Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true, tension: 80, friction: 10 }).start();
  }

  function hideCard() {
    Animated.timing(slideAnim, { toValue: 200, useNativeDriver: true, duration: 200 }).start(() => {
      setSelectedItem(null);
    });
  }

  // native: WebView onMessage 핸들러
  function handleNativeMessage(event: { nativeEvent: { data: string } }) {
    try {
      const { rank } = JSON.parse(event.nativeEvent.data);
      const item = items.find(it => it.rank === rank);
      if (item) showCard(item);
    } catch { /* ignore */ }
  }

  // web: iframe postMessage 리스너
  useEffect(() => {
    if (Platform.OS !== 'web') return;
    function onWebMessage(e: MessageEvent) {
      try {
        const { rank } = JSON.parse(e.data);
        const item = items.find(it => it.rank === rank);
        if (item) showCard(item);
      } catch { /* ignore */ }
    }
    window.addEventListener('message', onWebMessage);
    return () => window.removeEventListener('message', onWebMessage);
  }, [items]);

  const html = buildMapHtml(items, request.work_lat, request.work_lng, KAKAO_JS_KEY);

  const mapView = Platform.OS === 'web'
    ? React.createElement('iframe', {
        srcDoc: html,
        style: { flex: 1, border: 'none', width: '100%', height: '100%' } as React.CSSProperties,
        sandbox: 'allow-scripts allow-same-origin',
      })
    : React.createElement(WebView, {
        source: { html, baseUrl: 'https://youth-ht.app' },
        style: s.map,
        onMessage: handleNativeMessage,
        javaScriptEnabled: true,
        domStorageEnabled: true,
        originWhitelist: ['*'],
      });

  return (
    <View style={s.container}>
      {mapView}

      {selectedItem && (
        <>
          <TouchableOpacity style={s.backdrop} onPress={hideCard} activeOpacity={1} />
          <Animated.View style={[s.card, { transform: [{ translateY: slideAnim }] }]}>
            <View style={s.cardHandle} />
            <View style={s.cardTop}>
              <View style={[s.rankCircle, { backgroundColor: RANK_COLORS[(selectedItem.rank - 1) % RANK_COLORS.length] }]}>
                <Text style={s.rankText}>{selectedItem.rank}</Text>
              </View>
              <View style={s.cardInfo}>
                <Text style={s.cardName}>{selectedItem.region_name}</Text>
                <View style={s.tagRow}>
                  <Tag label={`월세 ${Math.round(selectedItem.rent_mean_won / 10000)}만원`} variant="default" />
                  <Tag label={`통근 ${selectedItem.commute_min}분`} variant="info" />
                  <Tag label={`${selectedItem.total_score.toFixed(0)}점`} variant="success" />
                </View>
              </View>
              <TouchableOpacity onPress={hideCard} style={s.closeBtn}>
                <Text style={s.closeText}>✕</Text>
              </TouchableOpacity>
            </View>

            <View style={s.metrics}>
              <MetricChip label="HUG" value={`${selectedItem.hug_acc_rate_pct.toFixed(1)}%`} />
              <MetricChip label="부담률" value={`${(selectedItem.burden_ratio * 100).toFixed(0)}%`} />
              <MetricChip label="6개월후" value={`${(selectedItem.future_burden_6m_ratio * 100).toFixed(0)}%`} />
              <MetricChip label="신뢰도" value={`${selectedItem.confidence}`} />
            </View>

            <TouchableOpacity
              style={s.detailBtn}
              onPress={() => { hideCard(); onCardPress(selectedItem); }}
              activeOpacity={0.85}
            >
              <Text style={s.detailBtnText}>AI 리포트 보기 →</Text>
            </TouchableOpacity>
          </Animated.View>
        </>
      )}
    </View>
  );
}

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <View style={s.chip}>
      <Text style={s.chipLabel}>{label}</Text>
      <Text style={s.chipValue}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },

  backdrop: { ...StyleSheet.absoluteFillObject, backgroundColor: 'transparent' },

  card: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: colors.bgCard,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    padding: spacing.md,
    paddingBottom: spacing.xl,
    ...shadow.lg,
  },
  cardHandle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.border,
    alignSelf: 'center',
    marginBottom: spacing.md,
  },
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: spacing.sm },
  rankCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.sm,
    flexShrink: 0,
  },
  rankText: { color: '#fff', fontSize: 18, fontWeight: '800' },
  cardInfo: { flex: 1 },
  cardName: { ...font.bodyBold, marginBottom: 6 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 5 },
  closeBtn: { padding: 4 },
  closeText: { fontSize: 16, color: colors.textMuted },

  metrics: { flexDirection: 'row', gap: 8, marginBottom: spacing.md },
  chip: {
    flex: 1,
    backgroundColor: colors.bgMuted,
    borderRadius: radius.md,
    paddingVertical: 8,
    alignItems: 'center',
  },
  chipLabel: { fontSize: 10, color: colors.textMuted, fontWeight: '500' },
  chipValue: { fontSize: 13, fontWeight: '700', color: colors.text, marginTop: 2 },

  detailBtn: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
  },
  detailBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
});
