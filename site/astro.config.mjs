import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://skills.mahimai.ca',
  integrations: [
    starlight({
      title: 'Voice AI Skills',
      description: 'Vendor-neutral engineering judgment for the coding agent building your voice agent.',
      favicon: '/favicon.ico',
      head: [
        { tag: 'link', attrs: { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32x32.png' } },
        { tag: 'link', attrs: { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/favicon-16x16.png' } },
      ],
      expressiveCode: {
        styleOverrides: {
          borderRadius: '0.5rem',
          frames: { editorActiveTabIndicatorTopColor: 'transparent', frameBoxShadowCssValue: 'none' },
        },
      },
      social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/mahimailabs/voice-ai-skills' }],
      editLink: { baseUrl: 'https://github.com/mahimailabs/voice-ai-skills/edit/main/' },
      customCss: [
        '@fontsource-variable/space-grotesk',
        '@fontsource-variable/jetbrains-mono',
        './src/styles/brand.css',
      ],
      components: {
        Head: './src/components/Head.astro',
        ThemeProvider: './src/components/ThemeProvider.astro',
        Footer: './src/components/Footer.astro',
      },
      sidebar: [
        { label: 'Start', items: [{ label: 'Home', link: '/' }, { label: 'Every “Do not”', link: '/do-not/' }, { label: 'Example review', link: '/example-review/' }] },
        { label: 'Skills', items: [{ autogenerate: { directory: 'skills' } }] },
        {
          label: 'Project',
          items: [
            { label: 'Neutrality policy', link: '/neutrality/' },
            { label: 'Q4 2026 roadmap', link: 'https://github.com/mahimailabs/voice-ai-skills/issues/1', attrs: { target: '_blank' } },
            { label: 'Contributing', link: 'https://github.com/mahimailabs/voice-ai-skills/blob/main/CONTRIBUTING.md', attrs: { target: '_blank' } },
            { label: 'Changelog', link: 'https://github.com/mahimailabs/voice-ai-skills/blob/main/CHANGELOG.md', attrs: { target: '_blank' } },
          ],
        },
      ],
    }),
  ],
});
