import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, radius } from '../theme';

type Variant = 'success' | 'warning' | 'danger' | 'info' | 'default';

interface Props {
  label: string;
  variant?: Variant;
  size?: 'sm' | 'md';
}

const VARIANT_STYLES: Record<Variant, { bg: string; text: string }> = {
  success: { bg: colors.successLight, text: colors.success },
  warning: { bg: colors.warningLight, text: colors.warning },
  danger: { bg: colors.dangerLight, text: colors.danger },
  info: { bg: colors.infoLight, text: colors.info },
  default: { bg: colors.bgMuted, text: colors.textSecondary },
};

export default function Tag({ label, variant = 'default', size = 'sm' }: Props) {
  const vs = VARIANT_STYLES[variant];
  return (
    <View style={[styles.tag, styles[size], { backgroundColor: vs.bg }]}>
      <Text style={[styles.text, size === 'md' ? styles.textMd : styles.textSm, { color: vs.text }]}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  tag: { borderRadius: radius.full, alignSelf: 'flex-start' },
  sm: { paddingHorizontal: 8, paddingVertical: 3 },
  md: { paddingHorizontal: 12, paddingVertical: 5 },
  text: { fontWeight: '600' },
  textSm: { fontSize: 11 },
  textMd: { fontSize: 13 },
});
