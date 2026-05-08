import React from 'react';
import { StyleProp, StyleSheet, TouchableOpacity, View, ViewStyle } from 'react-native';
import { colors, radius, shadow, spacing } from '../theme';

interface Props {
  children: React.ReactNode;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
  elevated?: boolean;
  borderColor?: string;
}

export default function Card({ children, onPress, style, elevated = false, borderColor }: Props) {
  const containerStyle = [styles.card, elevated && styles.elevated, borderColor ? { borderColor } : {}, style];
  if (onPress) {
    return (
      <TouchableOpacity onPress={onPress} activeOpacity={0.88} style={containerStyle}>
        {children}
      </TouchableOpacity>
    );
  }
  return <View style={containerStyle}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderLight,
    ...shadow.sm,
  },
  elevated: { ...shadow.md },
});
