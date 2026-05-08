import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';

interface Props {
  label: string;
  value: number;  // 0~1
  color: string;
}

export default function ScoreBar({ label, value, color }: Props) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${pct}%`, backgroundColor: color }]} />
      </View>
      <Text style={[styles.pct, { color }]}>{pct}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 5 },
  label: { width: 30, fontSize: 11, color: colors.textMuted, fontWeight: '500' },
  track: {
    flex: 1,
    height: 6,
    backgroundColor: colors.bgMuted,
    borderRadius: 3,
    overflow: 'hidden',
    marginHorizontal: 8,
  },
  fill: { height: '100%', borderRadius: 3 },
  pct: { width: 24, fontSize: 11, fontWeight: '600', textAlign: 'right' },
});
