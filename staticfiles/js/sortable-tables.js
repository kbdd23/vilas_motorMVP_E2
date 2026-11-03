(() => {
    const excludedHeaders = new Set(['accion', 'acciones', 'opciones']);
    const collator = new Intl.Collator('es', {
        numeric: true,
        sensitivity: 'base',
    });

    const normalize = (value) => value.replace(/\s+/g, ' ').trim();

    const valueFor = (row, column) => {
        const cell = row.cells[column];
        return normalize(cell?.dataset.sortValue || cell?.textContent || '');
    };

    const asDate = (value) => {
        const match = value.match(/^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})$/);
        if (match) {
            const [, day, month, rawYear] = match;
            const year = rawYear.length === 2 ? `20${rawYear}` : rawYear;
            const timestamp = Date.UTC(Number(year), Number(month) - 1, Number(day));
            return Number.isNaN(timestamp) ? null : timestamp;
        }

        const spanishMonths = {
            enero: 0, febrero: 1, marzo: 2, abril: 3, mayo: 4, junio: 5,
            julio: 6, agosto: 7, septiembre: 8, octubre: 9, noviembre: 10, diciembre: 11,
        };
        const spanishMatch = value.toLocaleLowerCase('es').match(/^(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})$/i);
        if (spanishMatch && spanishMonths[spanishMatch[2]] !== undefined) {
            return Date.UTC(Number(spanishMatch[3]), spanishMonths[spanishMatch[2]], Number(spanishMatch[1]));
        }

        const timestamp = /\d/.test(value) && (/^\d{4}-\d{2}-\d{2}$/.test(value) || /[a-z]/i.test(value))
            ? Date.parse(value)
            : NaN;
        return Number.isNaN(timestamp) ? null : timestamp;
    };

    const asNumber = (value) => {
        const numericPart = value.match(/^-?[\d\s.,]+/)?.[0] || '';
        const compact = numericPart.replace(/\s/g, '').replace(/\./g, '').replace(',', '.');
        return /^-?\d+(?:\.\d+)?$/.test(compact) ? Number(compact) : null;
    };

    const compareValues = (left, right) => {
        const leftDate = asDate(left);
        const rightDate = asDate(right);
        if (leftDate !== null && rightDate !== null) return leftDate - rightDate;

        const leftNumber = asNumber(left);
        const rightNumber = asNumber(right);
        if (leftNumber !== null && rightNumber !== null) return leftNumber - rightNumber;

        return collator.compare(left, right);
    };

    document.querySelectorAll('table').forEach((table) => {
        const headerRow = table.tHead?.rows[0];
        const body = table.tBodies[0];
        if (!headerRow || !body || body.rows.length < 2) return;

        const headers = Array.from(headerRow.cells);
        const sortableHeaders = [];
        table.classList.add('sortable-table');

        headers.forEach((header, column) => {
            const label = normalize(header.textContent || '');
            const labelKey = label.toLocaleLowerCase('es');
            if (!label || excludedHeaders.has(labelKey) || header.dataset.sortable === 'false') return;

            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'sort-button';
            button.textContent = label;
            button.setAttribute('aria-label', `Ordenar por ${label}`);

            header.textContent = '';
            header.append(button);
            header.classList.add('is-sortable');
            header.setAttribute('aria-sort', 'none');
            sortableHeaders.push(header);

            button.addEventListener('click', () => {
                const direction =
                    table.dataset.sortColumn === String(column) && table.dataset.sortDirection === 'ascending'
                        ? 'descending'
                        : 'ascending';
                const multiplier = direction === 'ascending' ? 1 : -1;
                const rows = Array.from(body.rows).map((row, index) => ({ row, index }));

                rows.sort((left, right) => {
                    const result = compareValues(valueFor(left.row, column), valueFor(right.row, column));
                    return result === 0 ? left.index - right.index : result * multiplier;
                });

                const fragment = document.createDocumentFragment();
                rows.forEach(({ row }) => fragment.append(row));
                body.append(fragment);

                sortableHeaders.forEach((item) => item.setAttribute('aria-sort', 'none'));
                header.setAttribute('aria-sort', direction);
                table.dataset.sortColumn = String(column);
                table.dataset.sortDirection = direction;
            });
        });
    });
})();
