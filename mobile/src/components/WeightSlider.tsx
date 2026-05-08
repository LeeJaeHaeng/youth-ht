import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { colors, font, radius } from '../theme';

export interface WeightValues {
  burden: number;
  commute: number;
  safety: number;
  future: number;
}

const LABELS: { key: keyof WeightValues; label: string; color: string }[] = [
  { key: 'burden', label: 'H+T 부담', color: colors.scoreBurden },
  { key: 'commute', label: '통근', color: colors.scoreCommute },
  { key: 'safety', label: '안전', color: colors.scoreSafety },
  { key: 'future', label: '미래변화', color: colors.scoreFuture },
];

const STEP = 5;
const MIN = 5;

function clamp(v: number) {
  return Math.min(100, Math.max(MIN, v));
}

function normalize(w: WeightValues): WeightValues {
  const total = w.burden + w.commute + w.safety + w.future;
  if (total === 0) return { burden: 40, commute: 30, safety: 20, future: 10 };
  const scale = 100 / total;
  return {
    burden: Math.round(w.burden * scale),
    commute: Math.round(w.commute * scale),
    safety: Math.round(w.safety * scale),
    future: Math.round(w.future * scale),
  };
}

interface Props {
  values: WeightValues;
  onChange: (v: WeightValues) => void;
}

export default function WeightSlider({ values, onChange }: Props) {
  const total = values.burden + values.commute + values.safety + values.future;
  const balanced = total === 100;

  function adjust(key: keyof WeightValues, delta: number) {
    const next = { ...values, [key]: clamp(values[key] + delta) };
    onChange(next);
  }

  function handleNormalize() {
    onChange(normalize(values));
  }

  return (
    <View style={s.container}>
      {LABELS.map(({ key, label, color }) => {
        const pct = values[key];
        return (
          <View key={key} style={s.row}>
            <View style={s.labelWrap}>
              <View style={[s.dot, { backgroundColor: color }]} />
              <Text style={s.label}>{label}</Text>
            </View>
            <View style={s.controls}>
              <TouchableOpacity
                style={s.btn}
                onPress={() => adjust(key, -STEP)}
                disabled={pct <= MIN}
                activeOpacity={0.7}
              >
                <Text style={[s.btnText, pct <= MIN && s.btnDisabled]}>−</Text>
              </TouchableOpacity>
              <View style={s.barWrap}>
                <View style={[s.bar, { width: `${pct}%` as any, backgroundColor: color }]} />
                <Text style={[s.pct, { color }]}>{pct}%</Text>
              </View>
              <TouchableOpacity
                style={s.btn}
                onPress={() => adjust(key, STEP)}
                disabled={pct >= 100 - MIN * 3}
                activeOpacity={0.7}
              >
                <Text style={[s.btnText, pct >= 100 - MIN * 3 && s.btnDisabled]}>+</Text>
              </TouchableOpacity>
            </View>
          </View>
        );
      })}
      <View style={s.totalRow}>
        <Text style={[s.totalLabel, !balanced && s.totalWarn]}>
          합계: {total}%{!balanced && ' (100%로 정규화 필요)'}
        </Text>
        {!balanced && (
          <TouchableOpacity onPress={handleNormalize} style={s.normBtn}>
            <Text style={s.normBtnText}>자동 조정</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  container: { gap: 10 },
  row: { gap: 6 },
  labelWrap: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  label: { ...font.caption, color: colors.textSecondary, fontWeight: '600' },

  controls: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  btn: {
    width: 32, height: 32, borderRadius: radius.sm,
    backgroundColor: colors.bgMuted,
    justifyContent: 'center', alignItems: 'center',
  },
  btnText: { fontSize: 20, fontWeight: '700', color: colors.text, lineHeight: 24 },
  btnDisabled: { color: colors.textMuted },

  barWrap: {
    flex: 1, height: 28,
    backgroundColor: colors.bgMuted,
    borderRadius: radius.sm,
    overflow: 'hidden',
    justifyContent: 'center',
    position: 'relative',
  },
  bar: { position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: radius.sm },
  pct: { fontSize: 12, fontWeight: '700', paddingLeft: 8, zIndex: 1 },

  totalRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingTop: 4,
    borderTopWidth: 1, borderTopColor: colors.borderLight,
  },
  totalLabel: { ...font.caption, color: colors.textSecondary },
  totalWarn: { color: colors.warning },
  normBtn: {
    paddingHorizontal: 10, paddingVertical: 4,
    backgroundColor: colors.warningLight, borderRadius: radius.full,
  },
  normBtnText: { fontSize: 11, color: colors.warning, fontWeight: '700' },
});
