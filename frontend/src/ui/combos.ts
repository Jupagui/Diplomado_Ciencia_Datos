import type { Regla } from '../services/api';

/** Un combo = un grupo de productos que se piden juntos, sin importar la dirección de la regla. */
export interface Combo {
  clave: string;      // productos en orden alfabético, unidos con « + »
  productos: string[];
  mejor: Regla;       // la dirección con mayor confianza: la que más conviene ofrecer
  reglas: Regla[];    // todas las direcciones del mismo combo
}

const productosDe = (texto: string) => texto.split(' + ');

/**
 * Apriori entrega una regla por dirección: «Limonada → Mojarra» y «Mojarra → Limonada»
 * (y en un trío, una regla por cada forma de partirlo). Para el dueño es un solo combo,
 * así que se agrupan por el conjunto de productos y se conserva el orden de la API (lift).
 */
export function agruparCombos(reglas: Regla[]): Combo[] {
  const grupos = new Map<string, Combo>();
  for (const r of reglas) {
    const productos = [...productosDe(r.antecedent), ...productosDe(r.consequent)].sort((a, b) => a.localeCompare(b, 'es'));
    const clave = productos.join(' + ');
    const grupo = grupos.get(clave);
    if (!grupo) {
      grupos.set(clave, { clave, productos, mejor: r, reglas: [r] });
    } else {
      grupo.reglas.push(r);
      if (r.confidence > grupo.mejor.confidence) grupo.mejor = r;
    }
  }
  return [...grupos.values()];
}
