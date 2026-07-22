import Image from 'next/image';
import mcataiLogo from '@/components/icons/mcatai-logo.svg';

export default function Logo({ className = '', ...props }: any) {
  return (
    <Image
      src={mcataiLogo}
      alt="MCATai Logo"
      width={64}
      height={64}
      priority
      className={className}
      {...props}
    />
  );
}