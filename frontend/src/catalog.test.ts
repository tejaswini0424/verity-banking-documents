import {describe,it,expect} from 'vitest';
import {pages,groups} from './catalog';
describe('navigation catalog',()=>{
 it('exposes exactly 32 unique routes',()=>{expect(pages).toHaveLength(32);expect(new Set(pages.map(p=>p.id)).size).toBe(32)});
 it('provides a title, description and category for every route',()=>{for(const p of pages){expect(p.title.length).toBeGreaterThan(3);expect(p.description.length).toBeGreaterThan(15);expect(groups.some(g=>g.name===p.group)).toBe(true)}});
});
