import {assetPattern,type Source} from './model.ts';

/** The package's display name must not choose an executable download extension. */
export function sourceFilename(source:Source){
  if(!assetPattern.test(source.asset))throw Error('Invalid original attachment type.');
  const ext=source.asset.slice(source.asset.lastIndexOf('.'));
  const leaf=source.name.split(/[\\/]/).pop()??'';
  const stem=leaf.replace(/\.[^.]*$/,'').replace(/[<>:"|?*\u0000-\u001f\u007f\u202a-\u202e\u2066-\u2069]/g,'_').replace(/[. ]+$/g,'').slice(0,150);
  return `${stem||'original'}${ext}`;
}
