import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getWarehouses } from "../services/warehouseService.js";

function WarehousesListPage() {
    const [warehouses, setWarehouses] = useState([]);

    useEffect(() => {
        getWarehouses()
            .then(setWarehouses)
            .catch(console.error);
    }, []);

    return (
        <div>
            <h1>Warehouses</h1>

            <Link to="/createwarehouse">
                <button>Create warehouse</button>
            </Link>

            <ul>
                {warehouses.map((wh) => (
                    <li key={wh.id}>
                        <Link to={`/warehouse/${wh.id}`}>{wh.name}</Link>
                        {typeof wh.floor_count === "number" ? ` — floors: ${wh.floor_count}` : ""}
                    </li>
                ))}
            </ul>

        </div>
    );
}

export default WarehousesListPage;
