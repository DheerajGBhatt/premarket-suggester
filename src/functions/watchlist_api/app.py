"""Watchlist API Lambda - REST API that generates watchlist on-demand."""
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

from shared_layer.services import WatchlistGeneratorService
from shared_layer.utils import format_api_response

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()


@app.get("/watchlist")
@tracer.capture_method
def get_watchlist() -> Dict[str, Any]:
    """Generate and return watchlist on-demand.

    Returns:
        dict: Watchlist with metadata
    """
    try:
        logger.info("Generating watchlist on-demand")

        service = WatchlistGeneratorService()
        result = service.generate_complete_watchlist()

        logger.info(f"Returning watch list with {result['metadata']['watchlist_size']} stocks")

        return format_api_response(
            success=True,
            data=result,
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error generating watchlist: {str(e)}", exc_info=True)
        return format_api_response(
            success=False,
            error={
                'code': 'WATCHLIST_ERROR',
                'message': 'Failed to generate watchlist'
            },
            status_code=500
        )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler for Watchlist API.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        dict: API response
    """
    return app.resolve(event, context)
